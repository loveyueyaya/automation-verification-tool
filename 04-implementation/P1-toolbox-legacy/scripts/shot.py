# -*- coding: utf-8 -*-
"""shot.py — 全屏/区域截图引擎（WGC 第一档，强制开关）。

引擎优先级：WGC(Windows.Graphics.Capture，WgcCapture.exe 桥接) >
            dxcam(DXGI Desktop Duplication) > mss(GDI 兜底)。
坐标契约：全部使用物理像素（DXGI 输出即物理分辨率，不受 DPI 缩放影响）。

强制开关（测试时大写强制开启 WGC）：
  UI_TOOLBOX_FORCE_WGC=1  强制 WGC：WGC 不可用时直接报错，不降级（测试模式）
  UI_TOOLBOX_WGC=0        禁用 WGC，直接走 dxcam（调试用）
  默认：WGC 存在则优先，失败自动降级 dxcam → mss

用法：
  python shot.py --monitor 0 --out D:/x.png            # 全屏物理像素截图
  python shot.py --monitor 0 --out D:/x.png --region 100,200,800,600
  python shot.py --test                                 # 引擎自检
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

env.set_dpi_awareness()

WGC_EXE = os.environ.get("UI_TOOLBOX_WGC_EXE",
                         os.path.join(os.path.dirname(
                             os.path.abspath(__file__)), "wgc", "WgcCapture.exe"))
FORCE_WGC = os.environ.get("UI_TOOLBOX_FORCE_WGC", "0") == "1"
DISABLE_WGC = os.environ.get("UI_TOOLBOX_WGC", "1") == "0"


class ShotEngine:
    """WGC > dxcam > mss。返回 numpy RGB 或 None。"""

    def __init__(self, monitor=0, output_color="RGB"):
        self.monitor = monitor
        self.output_color = output_color
        self._dx = None
        self._mss = None
        self._wgc_ready = os.path.isfile(WGC_EXE) and not DISABLE_WGC

    # ---- WGC（Windows.Graphics.Capture，经 C# 桥接）----
    def _try_wgc(self, region=None):
        if not self._wgc_ready:
            raise RuntimeError("WgcCapture.exe 不存在: %s" % WGC_EXE)
        tmp = os.path.join(os.environ.get("TEMP", "."), "_wgc_frame.png")
        cmd = [WGC_EXE, tmp, str(self.monitor)]
        if region:
            cmd += ["--region"] + region.split(",")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            raise RuntimeError("WGC 失败(%d): %s" % (r.returncode,
                                                     r.stderr.strip()[:300]))
        out = r.stdout.strip().splitlines()
        info = {}
        for line in out:
            try:
                info = json.loads(line)
                break
            except Exception:
                continue
        if not info.get("ok") or not os.path.isfile(tmp):
            raise RuntimeError("WGC 无有效输出: %s" % info)
        import numpy as np
        from PIL import Image
        img = np.asarray(Image.open(tmp).convert("RGB"))
        try:
            os.remove(tmp)
        except Exception:
            pass
        return img

    # ---- 区域参数解析：CLI 传 "x,y,w,h"，dxcam 需要 (left, top, right, bottom) ----
    @staticmethod
    def _region_box(region):
        """'x,y,w,h' -> (left, top, right, bottom)；无区域返回 None。"""
        if not region:
            return None
        try:
            x, y, w, h = [int(v) for v in str(region).split(",")]
        except Exception:
            raise ValueError("region 格式应为 x,y,w,h，实际: %s" % region)
        if w <= 0 or h <= 0:
            raise ValueError("region 宽高必须为正数，实际: %s" % region)
        return (x, y, x + w, y + h)

    # ---- dxcam（DXGI Desktop Duplication）----
    def _try_dxcam(self, region=None):
        if self._dx is None:
            import dxcam
            self._dx = dxcam.create(output_idx=self.monitor,
                                    output_color=self.output_color)
        box = self._region_box(region)
        # BUG-1 修复：此前此处恒为 self._dx.grab()，导致 --region 被静默丢弃
        img = self._dx.grab(region=box) if box else self._dx.grab()
        if img is None:
            # dxcam 在无新帧时返回 None；截图工具需要的是"当前画面"，
            # 交由上层降级到 mss（GDI）取帧，保证调用方始终拿到图像。
            raise RuntimeError("dxcam 未返回新帧（None）")
        return img

    # ---- mss（GDI 兜底）----
    def _try_mss(self, region=None):
        if self._mss is None:
            import mss
            self._mss = mss.mss()
        monitors = self._mss.monitors
        if self.monitor >= len(monitors):
            self.monitor = 0
        shot = self._mss.grab(monitors[self.monitor])
        import numpy as np
        img = np.asarray(shot)[:, :, :3]
        if self.output_color == "RGB":
            img = img[:, :, ::-1]
        img = np.ascontiguousarray(img)
        box = self._region_box(region)
        if box:
            # mss 无原生区域参数，按虚拟屏幕坐标裁剪（与 dxcam 行为对齐）
            left, top, right, bottom = box
            img = img[top:bottom, left:right]
        return img

    def grab(self, region=None):
        """WGC 优先；FORCE_WGC=1 时 WGC 失败直接抛错，绝不降级。"""
        errors = []
        if self._wgc_ready:
            try:
                return self._try_wgc(region)
            except Exception as e:
                errors.append("wgc(%s)" % e)
                if FORCE_WGC:
                    raise RuntimeError("强制 WGC 模式失败，禁止降级: %s" % e)
        try:
            return self._try_dxcam(region)
        except Exception as e:
            errors.append("dxcam(%s)" % e)
            try:
                return self._try_mss(region)
            except Exception as e2:
                raise RuntimeError("截图引擎全部失败: %s / mss(%s)"
                                   % (" / ".join(errors), e2))

    def grab_region(self, x, y, w, h):
        img = self.grab(region="%d,%d,%d,%d" % (x, y, w, h))
        import numpy as np
        return np.asarray(img)

    def close(self):
        if self._dx:
            try:
                self._dx.stop()
            except Exception:
                pass


# ---------- 模块级单例（审计：避免每次调用重新初始化 DXGI 设备） ----------
_ENGINE = None


def get_engine(monitor=0, output_color="RGB"):
    """全局唯一 ShotEngine；同一进程内复用 dxcam 设备（200-400ms 初始化只付一次）。"""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ShotEngine(monitor, output_color)
    return _ENGINE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--region", default=None, help="x,y,w,h")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    eng = ShotEngine(args.monitor)
    t0 = time.time()
    try:
        if args.test:
            img = eng.grab()
            dt = (time.time() - t0) * 1000
            engine = "wgc(强制)" if FORCE_WGC and eng._wgc_ready else \
                     ("wgc" if eng._wgc_ready else "dxcam")
            print(json.dumps({"ok": True, "engine": engine,
                              "size": [img.shape[1], img.shape[0]],
                              "ms": round(dt, 1)}, ensure_ascii=False))
            return
        if args.region:
            x, y, w, h = [int(v) for v in args.region.split(",")]
            img = eng.grab_region(x, y, w, h)
            desc = "region %d,%d %dx%d" % (x, y, w, h)
        else:
            img = eng.grab()
            desc = "fullscreen"
        dt = (time.time() - t0) * 1000
        from PIL import Image
        out_dir = os.path.dirname(args.out)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        Image.fromarray(img).save(args.out)
        engine = "wgc" if eng._wgc_ready else "dxcam"
        print(json.dumps({"ok": True, "engine": engine, "mode": desc,
                          "size": [img.shape[1], img.shape[0]],
                          "ms": round(dt, 1), "out": args.out},
                         ensure_ascii=False))
    finally:
        eng.close()


if __name__ == "__main__":
    main()
