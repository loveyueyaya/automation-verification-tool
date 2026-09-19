# -*- coding: utf-8 -*-
"""locate.py — 定位三路合一：OCR 坐标 + 句柄几何 + 模板匹配。

定位结果统一为 {x, y, w, h, cx, cy, source, confidence}（物理像素）。
三路互为校验：OCR 给"用户所见"的文字坐标，句柄给"精确控件"坐标，
模板给"图标/图片"坐标。优先级可配：handle > template > ocr。

用法：
  python locate.py ocr --text "豆包" --image D:/s.png            # OCR 找文字中心
  python locate.py handle --title "CookieSync" --class "ConsoleWindowClass"
  python locate.py template --tpl D:/icon.png --image D:/s.png   # 模板匹配
  python locate.py all --text "确定" --image D:/s.png            # 三路合一
  python locate.py verify --img1 a.png --img2 b.png --region 100,100,300,200
"""
import argparse
import json
import os
import subprocess
import sys
import time
from enum import Enum

# --- contracts 来源引导（P2-2 收尾 #1；feature flag 说明见 restore_p1_shim.py） ---
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # scripts 自身（env/shot/... 互相 import）
_IMPL = os.path.dirname(_HERE)                              # P1 遗留目录
_IMPL_ROOT = os.path.dirname(_IMPL)                         # 04-implementation
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _IMPL)                               # p1 模式：经 P1 目录 contracts shim（需先运行 restore_p1_shim.py）
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))  # 默认：契约层唯一实现
sys.path.append(os.path.join(_IMPL_ROOT, "P2-layers"))        # core 包：append 到末尾，不抢 contracts 解析优先级（p1/p2 两种模式都能用）
import env
import cache as cache_mod
from contracts import SourceEnum
from core.utils import jdefault   # P2-3 单源化：取代本文件原 _jdefault（与 uitool 那份重复且已漂移）

env.set_dpi_awareness()
PY = sys.executable
SCRIPTS = os.path.dirname(os.path.abspath(__file__))


def _run_ocr(image, text=None, region=None):
    """调 ocr.py 子进程（隔离模型加载），返回 items。"""
    cmd = [PY, os.path.join(SCRIPTS, "ocr.py"), "--image", image]
    if region:
        cmd += ["--region", region]
    if text:
        cmd += ["--filter", text]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        data = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return []
    return data.get("items", []) if data.get("ok") else []


def loc_by_ocr(image, text, region=None):
    items = _run_ocr(image, text=text, region=region)
    out = []
    for it in items:
        box = it.get("box") or []
        if len(box) < 4:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = min(xs), min(ys)
        w, h = max(xs) - x, max(ys) - y
        out.append({"x": x, "y": y, "w": w, "h": h,
                    "cx": int(x + w / 2), "cy": int(y + h / 2),
                    "source": SourceEnum.OCR, "text": it.get("text", ""),
                    "confidence": it.get("confidence", 0)})
    return out


def loc_by_handle(title=None, class_name=None):
    wins = env.find_windows(title_match=title, class_match=class_name)
    out = []
    for w in wins:
        r = w["rect"]
        out.append({"x": r[0], "y": r[1], "w": r[2] - r[0], "h": r[3] - r[1],
                    "cx": int((r[0] + r[2]) / 2), "cy": int((r[1] + r[3]) / 2),
                    "source": SourceEnum.HANDLE, "hwnd": w["hwnd"],
                    "title": w["title"], "class": w["class"]})
    return out


def loc_by_template(tpl_path, image_path, threshold=None):
    import cv2
    import numpy as np
    cfg = cache_mod.config()
    if threshold is None:
        threshold = cfg["sim_threshold"]
    tpl = cv2.imread(tpl_path, cv2.IMREAD_COLOR)
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if tpl is None or img is None:
        return []
    th, tw = tpl.shape[:2]
    res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return []
    x, y = max_loc
    return [{"x": x, "y": y, "w": tw, "h": th,
             "cx": x + tw // 2, "cy": y + th // 2,
             "source": SourceEnum.TEMPLATE, "confidence": float(max_val)}]


def loc_all(image, text=None, title=None, class_name=None,
            tpl_path=None, prefer="handle"):
    results = []
    if text:
        results += loc_by_ocr(image, text)
    if title or class_name:
        results += loc_by_handle(title, class_name)
    if tpl_path:
        results += loc_by_template(tpl_path, image)
    # 优先级排序：handle > template > ocr（键用枚举）
    order = {SourceEnum.HANDLE: 0, SourceEnum.TEMPLATE: 1, SourceEnum.OCR: 2}
    results.sort(key=lambda r: order.get(r.get("source"), 9))
    return results


def verify_region(img1, img2, region=None, threshold_pct=5.0):
    """两图区域对比，返回差异比例（%）。用于"验证"阶段判断界面是否变化。"""
    import cv2
    import numpy as np
    a = cv2.imread(img1, cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(img2, cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return {"ok": False, "error": "图片读取失败"}
    if a.shape != b.shape:
        return {"ok": False, "error": "尺寸不一致 %s vs %s" % (a.shape, b.shape)}
    if region:
        x, y, w, h = [int(v) for v in region.split(",")]
        a, b = a[y:y + h, x:x + w], b[y:y + h, x:x + w]
    diff = cv2.absdiff(a, b)
    pct = float((diff > 30).sum()) / diff.size * 100
    return {"ok": True, "diff_pct": round(pct, 3),
            "changed": pct > threshold_pct,
            "threshold_pct": threshold_pct}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ocr", "handle", "template", "all",
                                    "verify"])
    ap.add_argument("--text", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--class", dest="cls", default=None)
    ap.add_argument("--image", default=None)
    ap.add_argument("--tpl", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--threshold", type=float, default=None)
    a = ap.parse_args()

    if a.cmd == "ocr":
        print(json.dumps(loc_by_ocr(a.image, a.text, a.region),
                         ensure_ascii=False, default=jdefault))
    elif a.cmd == "handle":
        print(json.dumps(loc_by_handle(a.title, a.cls),
                         ensure_ascii=False, default=jdefault))
    elif a.cmd == "template":
        print(json.dumps(loc_by_template(a.tpl, a.image, a.threshold),
                         ensure_ascii=False, default=jdefault))
    elif a.cmd == "all":
        print(json.dumps(loc_all(a.image, a.text, a.title, a.cls, a.tpl),
                         ensure_ascii=False, default=jdefault))
    elif a.cmd == "verify":
        # verify --image img1 --tpl img2 (复用参数位传第二图)
        print(json.dumps(verify_region(a.image, a.tpl, a.region),
                         ensure_ascii=False, default=jdefault))


if __name__ == "__main__":
    main()
