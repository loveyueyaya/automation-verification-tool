# -*- coding: utf-8 -*-
"""ocr.py — PaddleOCR 本地识别服务（GPU，80% 显存上限，离线，坐标输出）。

约定：
  - 显存上限 = 显卡显存 * 0.8（FLAGS_gpu_memory_limit_mb），分配策略 auto_growth；
  - 输出统一 JSON：[{text, confidence, box:[[x,y]*4]}]，坐标为物理像素；
  - --region 支持先裁剪再识别（应对大图/小字：分块送入）；
  - 服务模式：--serve 后从 stdin 逐行读 {image, region} JSON，避免重复加载模型。

用法：
  python ocr.py --image D:/shot.png
  python ocr.py --image D:/shot.png --region 100,200,800,600
  echo '{"image":"D:/shot.png"}' | python ocr.py --serve
"""
import argparse
import json
import os
import sys


def _setup_gpu(mem_ratio=0.8):
    """在 import paddle 前设置显存上限（80%）与分配策略。"""
    import ctypes
    try:
        ctypes.windll.nvapi.nvapi_QueryInterface  # noqa 确保 nvapi 存在与否不影响
    except Exception:
        pass
    # 探测显存：用 paddle 前先用 nvidia-smi（无额外依赖）
    try:
        import subprocess
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        total_mb = int(out[0].split()[0]) if out else 12288
    except Exception:
        total_mb = 12288
    limit = int(total_mb * mem_ratio)
    os.environ.setdefault("FLAGS_gpu_memory_limit_mb", str(limit))
    os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
    os.environ.setdefault("FLAGS_use_pinned_memory", "true")
    return total_mb, limit


def load_ocr(lang="ch", gpu=True):
    total, limit = _setup_gpu()
    import paddle
    if gpu and paddle.device.is_compiled_with_cuda():
        paddle.set_device("gpu:0")
    from paddleocr import PaddleOCR
    kw = dict(use_doc_orientation_classify=False,
              use_doc_unwarping=False,
              use_textline_orientation=True,
              lang=lang)
    if gpu:
        kw["device"] = "gpu:0"
    ocr = PaddleOCR(**kw)
    ocr._gpu_total = total
    ocr._gpu_limit = limit
    return ocr


def recognize(ocr, image_path, region=None, text_filter=None):
    """识别图片/区域，返回规范化 JSON 列表。"""
    from PIL import Image
    import numpy as np
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if region:
        x, y, w, h = [int(v) for v in region.split(",")]
        img = img.crop((x, y, x + w, y + h))
        base = (x, y)
    else:
        base = (0, 0)
    tmp = os.path.join(os.environ.get("TEMP", "."), "_ocr_tmp.png")
    img.save(tmp)
    result = ocr.predict(input=tmp)
    items = []
    if result:
        for page in result:
            try:
                txts = page.get("rec_texts") or []
                scores = page.get("rec_scores") or []
                polys = page.get("rec_polys") or page.get("dt_polys") or []
            except Exception:
                continue
            for t, s, poly in zip(txts, scores, polys):
                if text_filter and text_filter not in t:
                    continue
                try:
                    import numpy as np
                    poly = np.asarray(poly, dtype=float).reshape(-1, 2).tolist() if poly is not None else []
                except Exception:
                    poly = []
                box = [[float(px) + base[0], float(py) + base[1]]
                       for px, py in poly]
                items.append({"text": str(t), "confidence": float(s),
                              "box": box})
    try:
        os.remove(tmp)
    except Exception:
        pass
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--filter", default=None, help="仅返回包含该子串的文本")
    ap.add_argument("--serve", action="store_true", help="stdio 服务模式")
    ap.add_argument("--gpu", action="store_true", default=True)
    args = ap.parse_args()

    if args.serve:
        ocr = load_ocr(gpu=args.gpu)
        print(json.dumps({"ready": True,
                          "gpu": getattr(ocr, "_gpu_total", None),
                          "limit_mb": getattr(ocr, "_gpu_limit", None)}),
              flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                items = recognize(ocr, req["image"], req.get("region"),
                                  req.get("filter"))
                print(json.dumps({"ok": True, "items": items},
                                 ensure_ascii=False), flush=True)
            except Exception as e:
                print(json.dumps({"ok": False, "error": str(e)}), flush=True)
        return

    if not args.image:
        print(json.dumps({"ok": False, "error": "需要 --image"}), flush=True)
        return
    ocr = load_ocr(gpu=args.gpu)
    items = recognize(ocr, args.image, args.region, args.filter)
    print(json.dumps({"ok": True, "count": len(items), "items": items},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
