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
import threading


def _gpu_total_mb():
    """用 NVIDIA 官方 pynvml 原生 API 读取显存总量（替代 subprocess 调 nvidia-smi）。

    优势：无进程启动开销（nvidia-smi 实测 151.79 ms/次），无需缓存，
    失败时回退默认值 12288 MiB。
    """
    try:
        import ctypes
        import pynvml
        # Windows 兼容：pynvml 默认只到 %ProgramFiles%/NVIDIA Corporation/NVSMI/nvml.dll 找库，
        # 部分机器（如本机）nvml.dll 仅存在于 System32，此处先按候选路径预加载。
        if getattr(pynvml, "nvmlLib", None) is None:
            cands = [
                os.path.join(os.getenv("ProgramFiles", "C:/Program Files"),
                             "NVIDIA Corporation", "NVSMI", "nvml.dll"),
                "nvml.dll",
            ]
            for cand in cands:
                try:
                    pynvml.nvmlLib = ctypes.CDLL(cand)
                    break
                except OSError:
                    continue
        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return int(info.total / 1024 / 1024)
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return 12288


def _setup_gpu(mem_ratio=0.8):
    """在 import paddle 前设置显存上限（80%）与分配策略。"""
    total_mb = _gpu_total_mb()
    limit = int(total_mb * mem_ratio)
    os.environ.setdefault("FLAGS_gpu_memory_limit_mb", str(limit))
    os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
    os.environ.setdefault("FLAGS_use_pinned_memory", "true")
    return total_mb, limit


_OCR_LOCK = threading.Lock()
_OCR = None


def get_ocr(lang="ch", gpu=True):
    """模块级单例：PaddleOCR 只初始化一次，后续调用直接复用（BUG-3 修复）。

    背景：PaddleOCR 初始化实测约 8.9 秒（模型加载），此前每次调用都重新
    load_ocr()，导致单次 OCR 端到端高达 10.9 秒。
    """
    global _OCR
    if _OCR is None:
        with _OCR_LOCK:
            if _OCR is None:
                _OCR = load_ocr(lang=lang, gpu=gpu)
    return _OCR


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
    ap.add_argument("--trace-id", default=None,
                    help="跨进程 trace 透传（P2-3）：由 uitool 注入，本脚本只接收不影响行为")
    ap.add_argument("--gpu", action="store_true", default=True)
    args = ap.parse_args()

    if args.serve:
        ocr = get_ocr(gpu=args.gpu)
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
    ocr = get_ocr(gpu=args.gpu)
    items = recognize(ocr, args.image, args.region, args.filter)
    print(json.dumps({"ok": True, "count": len(items), "items": items},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
