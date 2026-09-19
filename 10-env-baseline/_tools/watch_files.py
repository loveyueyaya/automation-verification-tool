# -*- coding: utf-8 -*-
"""文件消失监控：定时采样关键目录的文件数/总大小，落盘 csv + 逐次打印。
用途：实证 site-packages 是否存在持续删除行为（不猜测，只看数据）。
"""
import os
import sys
import time
import json
import datetime

SP = r"C:\Program Files\Python313\Lib\site-packages"
WATCH = ["cv2", "paddle", "dxcam", "numpy", "PIL", "paddleocr", "paddlex", "mss"]
OUT = r"F:\自动化验证工具\10-env-baseline\_evidence\_watch_log.jsonl"


def measure(name):
    p = os.path.join(SP, name)
    if not os.path.isdir(p):
        return {"exists": False, "files": 0, "bytes": 0}
    n = 0
    b = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            fp = os.path.join(dp, f)
            n += 1
            try:
                b += os.path.getsize(fp)
            except OSError:
                pass
    return {"exists": True, "files": n, "bytes": b}


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    for i in range(rounds):
        snap = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "data": {k: measure(k) for k in WATCH}}
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
        line = " ".join(f"{k}={v['files']}" for k, v in snap["data"].items())
        print(f"[{snap['ts']}] {line}", flush=True)
        if i < rounds - 1:
            time.sleep(interval)


if __name__ == "__main__":
    main()
