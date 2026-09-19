# -*- coding: utf-8 -*-
"""第四步实测：OCR 误识别率量化 + 官方调优参数（enable_hpi / fp16 / det_limit_side_len）实测收益
只读项目代码，不修改任何项目文件。"""
import os
import sys
import time
import json
import subprocess

P1 = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"
SCRIPTS = os.path.join(P1, "scripts")
sys.path.insert(0, SCRIPTS)

T = r"F:\wordbuddy\2026-09-18-21-23-01"
FULL = os.path.join(T, "_bench_full.png")
CROP = os.path.join(T, "_bench_crop.png")


def vram():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                              "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return int(out.splitlines()[0])
    except Exception:
        return -1


# 1) 取一张真实截图（走项目 shot.py 的引擎）
sys.argv = ["shot.py", "--out", FULL]
import runpy
t0 = time.perf_counter()
runpy.run_path(os.path.join(SCRIPTS, "shot.py"), run_name="__main__")
print(f"[shot] 全屏截图耗时 {(time.perf_counter()-t0)*1000:.0f} ms, size={os.path.getsize(FULL)//1024} KB")

from PIL import Image
im = Image.open(FULL)
im.crop((1500, 80, 1800, 140)).save(CROP)
print(f"[crop] {im.size} -> {Image.open(CROP).size}")

base_vram = vram()
print(f"[vram] 基线显存占用 {base_vram} MiB")

CONFIGS = [
    ("baseline（现项目参数）", dict(use_doc_orientation_classify=False,
                                    use_doc_unwarping=False,
                                    use_textline_orientation=True, lang="ch",
                                    device="gpu:0")),
    ("+enable_hpi=True", dict(use_doc_orientation_classify=False,
                              use_doc_unwarping=False,
                              use_textline_orientation=True, lang="ch",
                              device="gpu:0", enable_hpi=True)),
    ("+precision=fp16", dict(use_doc_orientation_classify=False,
                             use_doc_unwarping=False,
                             use_textline_orientation=True, lang="ch",
                             device="gpu:0", precision="fp16")),
    ("+det_limit_side_len=640", dict(use_doc_orientation_classify=False,
                                     use_doc_unwarping=False,
                                     use_textline_orientation=True, lang="ch",
                                     device="gpu:0",
                                     text_det_limit_side_len=640)),
]

print("\n=== 各配置实测（每组：模型加载 + 裁剪推理 x2 + 全屏推理 x1）===")
results = []
for name, kw in CONFIGS:
    try:
        t0 = time.perf_counter()
        import paddle
        paddle.set_device("gpu:0")
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(**kw)
        load_ms = (time.perf_counter() - t0) * 1000
        ts_crop = []
        for _ in range(2):
            t = time.perf_counter()
            ocr.predict(input=CROP)
            ts_crop.append((time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        res = ocr.predict(input=FULL)
        full_ms = (time.perf_counter() - t) * 1000
        v = vram()
        items = []
        for page in (res or []):
            items += list(page.get("rec_texts") or [])
            scores = list(page.get("rec_scores") or [])
        results.append((name, load_ms, ts_crop, full_ms, v, len(items),
                        sum(1 for s in scores if s < 0.8), len(scores)))
        print(f"{name:26s} load={load_ms:7.0f}ms  crop={ts_crop[0]:6.1f}/{ts_crop[1]:6.1f}ms  "
              f"full={full_ms:7.0f}ms  vram={v}MiB  items={len(items)}")
        if name.startswith("baseline"):
            print(f"    └ 全屏识别 {len(scores)} 条，其中 confidence<0.8 的 {sum(1 for s in scores if s<0.8)} 条 "
                  f"（{sum(1 for s in scores if s<0.8)/max(len(scores),1)*100:.1f}%）")
            low = [(t, round(s, 3)) for t, s in zip(items, scores) if s < 0.6][:10]
            print(f"    └ conf<0.6 样例：{low}")
        del ocr
    except Exception as e:
        print(f"{name:26s} FAILED: {type(e).__name__}: {str(e)[:160]}")

print("\n=== 汇总 ===")
print(f"{'配置':26s} {'加载ms':>8s} {'裁剪ms':>8s} {'全屏ms':>8s} {'显存MiB':>8s}")
for name, load_ms, ts_crop, full_ms, v, *_ in results:
    print(f"{name:26s} {load_ms:8.0f} {ts_crop[-1]:8.1f} {full_ms:8.0f} {v:8d}")

for f in (FULL, CROP):
    try:
        os.remove(f)
    except Exception:
        pass
print("\n临时截图已清理")
