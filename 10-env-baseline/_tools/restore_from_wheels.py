# -*- coding: utf-8 -*-
"""覆盖法恢复：把 wheel 里的文件复制进 site-packages，只补不删。

规则（项目实测结论）：
  - 禁用 pip --force-reinstall（共享命名空间包会连带卸载 numpy）
  - 只写入，不删除任何已存在文件
  - RECORD 已存在时保留旧的（避免元数据被降级）；不存在时补上

用法：python restore_from_wheels.py <wheel_dir> [包名前缀过滤...]
"""
import os
import sys
import zipfile
import tempfile
import shutil

SP = r"C:\Program Files\Python313\Lib\site-packages"


def restore(whl):
    name = os.path.basename(whl)
    tmp = tempfile.mkdtemp(prefix="rsz_")
    written = skipped = 0
    try:
        with zipfile.ZipFile(whl) as z:
            z.extractall(tmp)
        for root, _, files in os.walk(tmp):
            for fn in files:
                src = os.path.join(root, fn)
                rel = os.path.relpath(src, tmp)
                dst = os.path.join(SP, rel)
                if rel.replace("\\", "/").endswith("/RECORD") and os.path.exists(dst):
                    skipped += 1
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(src, "rb") as a, open(dst, "wb") as b:
                    b.write(a.read())
                written += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {name:62} -> 写入 {written:>5} 文件 (保留旧 RECORD {skipped})")
    return written


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    d = args[0]
    filt = args[1:]
    whls = sorted(f for f in os.listdir(d) if f.endswith(".whl"))
    if filt:
        whls = [w for w in whls if any(k.lower() in w.lower() for k in filt)]
    print(f"待恢复 {len(whls)} 个 wheel（目标 {SP}）")
    total = 0
    for w in whls:
        total += restore(os.path.join(d, w))
    print(f"\n合计写入 {total} 个文件")


if __name__ == "__main__":
    sys.exit(main())
