# -*- coding: utf-8 -*-
"""testbar.py v5 — 测试状态控制台（覆盖条 + 控制面板 + 全局热键 + 性能监控 + 诊断 + 日志）。

v5 变更（2026-09-16 审计整改）：
  1. force_caps 默认 6 轮 → 3 轮（27s 冻结感过强）
  2. run_diag 在 panel=None（--no-panel）时不再 AttributeError
  3. 与 ui-toolbox 同步：env/shot/ocr/timeline/uitool 审计修复对齐

用法（Windows）：
  & "C:/Program Files/Python313/python.exe" testbar.py
  & "C:/Program Files/Python313/python.exe" testbar.py --no-panel
"""
import argparse
import ctypes
import json
import os
import queue
import struct
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)      # exe 所在目录（日志/配置写这里）
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import perfmon
import diagnose

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# ---------- 常量 ----------
VK_CAPITAL = 0x14
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
KEYEVENTF_KEYUP = 0x0002
ABM_GETTASKBARPOS = 0x00000005
SRCCOPY = 0x00CC0020

C_BG0 = "#151622"
C_BG1 = "#1D1F2E"
C_CHIP = "#2A2D3E"
C_TEXT = "#EDEEF7"
C_SUB = "#9BA0B8"
C_ACCENT = "#7C6CF0"
C_GREEN = "#34D399"
C_YELLOW = "#FBBF24"
C_RED = "#F87171"
C_GRAY = "#8B90A8"
C_LINE = "#2E3145"
C_CPU, C_GPU, C_MEM = "#38BDF8", "#A78BFA", "#34D399"

STATE_META = {
    "IDLE":       {"text": "待命",       "color": C_GRAY},
    "TESTING":    {"text": "正在测试中", "color": C_GREEN},
    "PAUSED":     {"text": "测试已暂停", "color": C_YELLOW},
    "TERMINATED": {"text": "测试已终止", "color": C_RED},
}

# 操作语义：uid -> (默认键, 备选键, 操作名)
OPS = {
    1: (0x79, 0x2D, "启动"),   # F10 / INSERT
    2: (0x7A, 0x24, "暂停"),   # F11 / HOME
    3: (0x7B, 0x21, "终止"),   # F12 / PAGEUP
}

KEY_MAP = {}
for i in range(1, 25):
    KEY_MAP["F%d" % i] = 0x6F + i
KEY_MAP.update({
    "INSERT": 0x2D, "INS": 0x2D, "HOME": 0x24, "PAGEUP": 0x21, "PGUP": 0x21,
    "PAGEDOWN": 0x22, "PGDN": 0x22, "DELETE": 0x2E, "DEL": 0x2E, "END": 0x23,
    "SPACE": 0x20, "ESC": 0x1B, "TAB": 0x09, "ENTER": 0x0D,
    "BACKSPACE": 0x08, "NUMLOCK": 0x90, "SCROLLLOCK": 0x91,
})
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY_MAP[c] = ord(c)
for c in "0123456789":
    KEY_MAP[c] = ord(c)
VK_NAME = {v: k for k, v in KEY_MAP.items()}

DEFAULT_TARGET = "cookie_sync.exe"

# 已知会接管键盘注入的远程控制软件（导致 CapsLock toggle 排队/失效）
REMOTE_PROCS = ["wujie", "sunloginclient", "todesk", "anydesk", "rper",
                "uu", "mstsc", "qclient"]


def key_name(vk):
    return VK_NAME.get(vk, "VK%d" % vk)


def remote_tools_running():
    """用 psutil（原生 API，无外部进程）检测正在运行的远程控制软件。"""
    try:
        import psutil
    except Exception:
        return []
    found = []
    try:
        names = set()
        for p in psutil.process_iter(["name"]):
            try:
                nm = (p.info.get("name") or "").lower()
            except Exception:
                continue
            if not nm:
                continue
            base = nm.split(".")[0]
            for rp in REMOTE_PROCS:
                if base == rp and rp not in names:
                    names.add(rp)
                    found.append(rp)
    except Exception:
        pass
    return found


# ---------- 系统能力 ----------
def caps_state():
    # GetAsyncKeyState 返回全局键状态；GetKeyState 是线程局部且注入后可能读到旧值
    return bool(user32.GetAsyncKeyState(VK_CAPITAL) & 1)


def force_caps(on, max_round=3):
    """强制 CapsLock 状态。
    远程控制软件（无界趣连等）会把键盘注入异步排队（延迟 1~2s 才生效），
    因此达到目标后等 2.5s 确认（让队列清空），被冲掉再补，最多 max_round 轮。
    审计：默认 6 轮 → 3 轮（27s 冻结感过强，3 轮足够覆盖队列深度）。"""
    for _ in range(max_round):
        if caps_state() == on:
            time.sleep(2.5)          # 让可能排队的 toggle 全部生效
            if caps_state() == on:
                return True
            continue                 # 被后续队列冲掉，继续补
        user32.keybd_event(VK_CAPITAL, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(VK_CAPITAL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(2.0)              # 等队列处理
    return caps_state() == on


class APPBAORDATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uCallbackMessage", wintypes.UINT),
                ("uEdge", wintypes.UINT),
                ("rc", wintypes.RECT),
                ("lParam", ctypes.c_long)]


def taskbar_rect():
    shell32 = ctypes.windll.shell32
    ab = APPBAORDATA()
    ab.cbSize = ctypes.sizeof(APPBAORDATA)
    if shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(ab)):
        r = ab.rc
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    return (0, 1380, 2560, 60)


def proc_running(name):
    """用 psutil 查目标程序是否运行，返回 PID 或 None。"""
    try:
        import psutil
    except Exception:
        return None
    base = os.path.splitext(name)[0].lower()
    try:
        for p in psutil.process_iter(["name"]):
            try:
                nm = (p.info.get("name") or "").lower()
            except Exception:
                continue
            if nm.split(".")[0] == base:
                return p.pid
    except Exception:
        pass
    return None


def gdi_screenshot(path):
    """GDI 全屏截图存 BMP（无第三方依赖；桌面会话内可靠）。返回 True/False。"""
    try:
        sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        hdc = user32.GetDC(None)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, sw, sh)
        gdi32.SelectObject(mdc, bmp)
        gdi32.BitBlt(mdc, 0, 0, sw, sh, hdc, 0, 0, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32),
                        ("biWidth", ctypes.c_int32),
                        ("biHeight", ctypes.c_int32),
                        ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16),
                        ("biCompression", ctypes.c_uint32),
                        ("biSizeImage", ctypes.c_uint32),
                        ("biXPelsPerMeter", ctypes.c_int32),
                        ("biYPelsPerMeter", ctypes.c_int32),
                        ("biClrUsed", ctypes.c_uint32),
                        ("biClrImportant", ctypes.c_uint32)]

        bh = BITMAPINFOHEADER()
        bh.biSize = 40
        bh.biWidth, bh.biHeight = sw, sh
        bh.biPlanes, bh.biBitCount = 1, 24
        row = (sw * 3 + 3) & ~3
        buf = ctypes.create_string_buffer(row * sh)
        gdi32.GetDIBits(mdc, bmp, 0, sh, buf, ctypes.byref(bh), 0)
        # BMP 文件头（BGR 底部上行）
        head = struct.pack("<2sIHHI", b"BM", 54 + row * sh, 0, 0, 54)
        with open(path, "wb") as f:
            f.write(head)
            f.write(bytes(bh)[:40])
            f.write(buf.raw)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(None, hdc)
        return True
    except Exception:
        return False


# ---------- 日志 ----------
class Logger:
    def __init__(self, base_dir):
        self.dir = os.path.join(base_dir, "logs")
        self.ev_dir = os.path.join(self.dir, "evidence")
        os.makedirs(self.ev_dir, exist_ok=True)
        self.path = os.path.join(self.dir, "testbar_%s.jsonl" %
                                 time.strftime("%Y%m%d"))
        self.buffer = []

    def log(self, action, state=None, detail=""):
        rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S") + ".%03d" %
               (int(time.time() * 1000) % 1000),
               "action": action, "state": state or "", "detail": detail}
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        self.buffer.append(rec)
        self.buffer = self.buffer[-40:]


# ---------- 全局热键 ----------
class HotkeyManager:
    def __init__(self, on_event):
        self.keys = {uid: OPS[uid][0] for uid in OPS}   # uid -> vk
        self.on_event = on_event
        self.conflicts = {}
        self._q = queue.Queue()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        for uid in OPS:
            vk = self.keys.get(uid)
            if vk is not None:
                ok = user32.RegisterHotKey(None, uid, MOD_NOREPEAT, vk) != 0
                if not ok:
                    self.conflicts[uid] = vk
                    self._q.put(("conflict", uid, vk))

        class MSG(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                        ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                        ("time", wintypes.DWORD), ("pt", wintypes.POINT)]
        msg = MSG()
        while not self._stop.is_set():
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0:
                break
            if msg.message == WM_HOTKEY:
                self._q.put(("hotkey", int(msg.wParam)))

    def poll(self):
        out = []
        while True:
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                break
        return out

    def _free(self, uid):
        user32.UnregisterHotKey(None, uid)

    def probe(self, vk):
        """探测某键是否可全局注册（可注册返回 True，占位立即释放）。"""
        try:
            ok = user32.RegisterHotKey(None, 0x6FF0, MOD_NOREPEAT, vk) != 0
            if ok:
                user32.UnregisterHotKey(None, 0x6FF0)
            return bool(ok)
        except Exception:
            return False

    def apply(self, uid, vk):
        """重绑：注销旧键 → 注册新键。成功返回 True；失败（冲突）返回 False。"""
        self._free(uid)
        if user32.RegisterHotKey(None, uid, MOD_NOREPEAT, vk):
            self.keys[uid] = vk
            self.conflicts.pop(uid, None)
            return True
        self.conflicts[uid] = vk
        return False

    def drop_conflict(self, uid):
        """强制继续：放弃该键的注册与监听。"""
        self._free(uid)
        self.keys.pop(uid, None)
        self.conflicts.pop(uid, None)

    def stop(self):
        self._stop.set()
        for uid in OPS:
            self._free(uid)
        if self._thread and self._thread.ident:
            user32.PostThreadMessageW(self._thread.ident, WM_QUIT, 0, 0)


# ---------- 渲染 ----------
def round_rect(cv, x1, y1, x2, y2, r, **kw):
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
              x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2,
              x1, y2 - r, x1, y1, x1 + r, y1]
    return cv.create_polygon(points, smooth=True, **kw)


def chip(cv, x, y, w, text, color, font_size=9):
    round_rect(cv, x, y - 9, x + w, y + 9, 8, fill=C_CHIP,
               outline=color, width=1)
    cv.create_text(x + w / 2, y, text=text, fill=color,
                   font=("Microsoft YaHei UI", font_size))


# ---------- 性能卡（参照硬件监控风格） ----------
class PerfCard(tk.Canvas):
    W, H = 226, 195

    def __init__(self, master, title, icon="◉"):
        super().__init__(master, width=self.W, height=self.H,
                         bg=C_BG0, highlightthickness=0)
        self.title = title
        self.icon = icon
        self._data = {"cpu": [], "gpu": [], "mem": [], "vram": []}
        self._mem_max = 100

    def update_data(self, series):
        self._data = series
        vals = [v for v in series.get("mem", []) if v]
        self._mem_max = max(100, max(vals)) if vals else 100
        self._draw()

    def _bar(self, cv, x, y, w, frac, color):
        round_rect(cv, x, y, x + w, y + 8, 4, fill="#1A1D2E", outline="")
        fw = int(w * max(0.0, min(1.0, frac)))
        if fw > 2:
            round_rect(cv, x, y, x + fw, y + 8, 4, fill=color, outline="")

    def _row(self, cv, y, label, value, sub, frac, color):
        # 图标块
        cv.create_rectangle(12, y - 10, 26, y + 4, fill=color, outline="")
        cv.create_text(19, y - 3, text=label[0], fill="#101322",
                       font=("Microsoft YaHei UI", 8, "bold"))
        cv.create_text(34, y - 3, text=label, anchor="w", fill=C_SUB,
                       font=("Microsoft YaHei UI", 9))
        cv.create_text(self.W - 12, y - 7, text=value, anchor="e",
                       fill=C_TEXT, font=("Consolas", 12, "bold"))
        if sub:
            cv.create_text(self.W - 12, y + 8, text=sub, anchor="e",
                           fill=C_SUB, font=("Microsoft YaHei UI", 7))
        self._bar(cv, 34, y + 9, self.W - 46, frac, color)

    def _draw(self):
        cv = self
        cv.delete("all")
        W, H = self.W, self.H
        round_rect(cv, 1, 1, W - 1, H - 1, 10, fill=C_BG1,
                   outline=C_LINE, width=1)
        cv.create_oval(12, 10, 24, 22, fill=C_ACCENT, outline="")
        cv.create_text(18, 16, text=self.icon, fill=C_TEXT,
                       font=("Microsoft YaHei UI", 8))
        cv.create_text(32, 16, text=self.title, anchor="w",
                       fill=C_TEXT, font=("Microsoft YaHei UI", 10, "bold"))
        cv.create_line(10, 30, W - 10, 30, fill=C_LINE, width=1)

        d = self._data
        cpu = d.get("cpu") or [0]
        gpu = d.get("gpu") or [0]
        mem = d.get("mem") or [0]
        cv_cpu = cpu[-1] if cpu[-1] is not None else 0
        cv_gpu = gpu[-1] if gpu[-1] is not None else 0
        cv_mem = mem[-1] if mem[-1] is not None else 0

        vram_mb = 0.0
        vram_tot = 0.0
        vram = d.get("vram") or []
        if vram and vram[-1]:
            vram_mb = vram[-1]
        try:
            gc = self._data.get("gpu_card") or {}
        except Exception:
            gc = {}
        # vram 总量取最后一次 snapshot 的 gpu_card（由 update_data 附加）
        vram_tot = getattr(self, "_vram_total", 0.0)

        self._row(cv, 52, "CPU", "%d%%" % round(cv_cpu), None,
                  cv_cpu / 100.0, C_CPU)
        gpu_sub = ""
        if vram_tot > 0:
            gpu_sub = "VRAM %.1f/%.1fG" % (vram_mb / 1024.0, vram_tot / 1024.0)
        self._row(cv, 104, "GPU", "%d%%" % round(cv_gpu), gpu_sub,
                  cv_gpu / 100.0, C_GPU)
        self._row(cv, 156, "内存", "%dMB" % round(cv_mem), None,
                  cv_mem / float(self._mem_max), C_MEM)

    def set_vram_total(self, mb):
        self._vram_total = mb
        self._draw()


# ---------- 控制面板 ----------
class ControlPanel(tk.Toplevel):
    W, H = 486, 800

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.configure(bg="#010203")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#010203")
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        self.geometry("%dx%d+%d+%d" % (self.W, self.H, sw - self.W - 24, 24))
        self.cv = tk.Canvas(self, width=self.W, height=self.H,
                            bg="#010203", highlightthickness=0)
        self.cv.pack()
        self._drag = None
        self.cv.bind("<ButtonPress-1>", self._drag_start)
        self.cv.bind("<B1-Motion>", self._drag_move)
        self.chart_console = PerfCard(self, "测试控制台", "C")
        self.chart_target = PerfCard(self, "目标程序", "T")
        self.chart_console.place(x=12, y=256)
        self.chart_target.place(x=248, y=256)
        self._diag_result = []
        self._key_entries = {}
        self._key_feedback = {}
        self.draw()

    def _drag_start(self, e):
        area = getattr(self, "_diag_area", None)
        if area and area[0] <= e.x <= area[2] and area[1] <= e.y <= area[3]:
            self.app.run_diag()
            return
        # 快捷键应用按钮区
        for uid, (x1, y1, x2, y2) in getattr(self, "_apply_areas", {}).items():
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self._apply_key(uid)
                return
        self._drag = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _drag_move(self, e):
        if self._drag:
            self.geometry("+%d+%d" % (e.x_root - self._drag[0],
                                      e.y_root - self._drag[1]))

    def _apply_key(self, uid):
        name = self._key_entries[uid].get()
        vk = KEY_MAP.get(name.strip().upper())
        if vk is None:
            self._key_feedback[uid] = ("无效键名", C_RED)
            self.app.log("改键失败", detail="%s 无效键名 %r" % (OPS[uid][2], name))
            self.draw()
            return
        if self.app.hk.apply(uid, vk):
            self._key_feedback[uid] = ("已绑定 %s" % key_name(vk), C_GREEN)
            self.app.log("改键", detail="%s → %s" % (OPS[uid][2], key_name(vk)))
            # 同步输入框显示新键名
            ent = self._key_entries.get("key_%d" % uid)
            if ent is not None:
                ent.delete(0, "end")
                ent.insert(0, key_name(vk))
        else:
            self._key_feedback[uid] = ("冲突！%s 被占用" % key_name(vk), C_RED)
            self.app.log("改键失败", detail="%s → %s 已被其他程序占用" %
                         (OPS[uid][2], key_name(vk)))
            # 侦查备选并推荐
            fb = OPS[uid][1]
            if self.app.hk.probe(fb):
                self._key_feedback[uid] = ("推荐改用 %s" % key_name(fb), C_YELLOW)
                self.app.log("冲突推荐", detail="%s 推荐改用 %s" %
                             (key_name(vk), key_name(fb)))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        W = self.W
        round_rect(cv, 6, 6, W - 6, self.H - 6, 18,
                   fill=C_BG0, outline=C_LINE, width=1)
        cv.create_oval(26, 28, 38, 40, fill=C_ACCENT, outline="")
        cv.create_text(46, 34, text="UI 自动化测试控制台", anchor="w",
                       fill=C_TEXT, font=("Microsoft YaHei UI", 14, "bold"))
        cv.create_text(46, 50, text="PID %d" % os.getpid(), anchor="w",
                       fill=C_GRAY, font=("Microsoft YaHei UI", 8))
        cv.create_text(W - 34, 34, text="✕", fill=C_SUB,
                       font=("Microsoft YaHei UI", 12), tags=("close",))
        cv.tag_bind("close", "<Button-1>", lambda e: self.app.request_exit())

        st = STATE_META[self.app.state]
        cx, cy = W / 2, 86
        cv.create_oval(cx - 15, cy - 15, cx + 15, cy + 15, fill=st["color"],
                       outline="")
        cv.create_oval(cx - 19, cy - 19, cx + 19, cy + 19, fill="",
                       outline=st["color"], width=1)
        cv.create_text(cx, cy + 38, text=st["text"], fill=st["color"],
                       font=("Microsoft YaHei UI", 13, "bold"))
        cv.create_text(cx, cy + 58, text="CapsLock: %s" % self._caps_label(),
                       fill=C_SUB, font=("Microsoft YaHei UI", 10))

        # 按钮
        bw, bh, gap = 96, 44, 14
        bx = (W - (bw * 3 + gap * 2)) / 2
        by = 168
        pause_label = "▶ 继续" if self.app.state == "PAUSED" else "⏸ 暂停"
        pause_color = C_YELLOW if self.app.state == "PAUSED" else C_CHIP
        btns = [("▶ 开始", self.app.start, C_ACCENT, C_TEXT),
                (pause_label, self.app.pause, pause_color, C_TEXT),
                ("⏹ 终止", self.app.terminate, "#3A2A2E", C_RED)]
        for i, (label, cb, fill, fg) in enumerate(btns):
            x = bx + i * (bw + gap)
            round_rect(cv, x, by, x + bw, by + bh, 10, fill=fill,
                       tags=("btn_%d" % i,))
            cv.create_text(x + bw / 2, by + bh / 2, text=label, fill=fg,
                           font=("Microsoft YaHei UI", 11, "bold"),
                           tags=("btn_%d" % i,))
            cv.tag_bind("btn_%d" % i, "<Button-1>", lambda e, f=cb: f())

        # 目标程序
        ty = by + bh + 18
        cv.create_text(28, ty + 4, text="目标程序", fill=C_SUB,
                       font=("Microsoft YaHei UI", 10))
        tname = self.app.target_display
        tcolor = C_GREEN if self.app.target_ok else C_YELLOW
        round_rect(cv, 92, ty - 10, 300, ty + 18, 8, fill=C_CHIP,
                   outline=tcolor, width=1)
        cv.create_text(196, ty + 4, text="%s %s" % (
            tname, "运行中" if self.app.target_ok else "未运行"),
                       fill=tcolor, font=("Microsoft YaHei UI", 9))
        round_rect(cv, 312, ty - 10, 402, ty + 18, 8, fill=C_ACCENT,
                   tags=("browse",))
        cv.create_text(357, ty + 4, text="浏览…", fill=C_TEXT,
                       font=("Microsoft YaHei UI", 9, "bold"), tags=("browse",))
        cv.tag_bind("browse", "<Button-1>", lambda e: self.app.browse_target())

        # 性能卡标题（置于卡片上方 y=242）
        cv.create_text(12, 246, text="实时性能（1s 刷新）", anchor="w",
                       fill=C_SUB, font=("Microsoft YaHei UI", 8))

        # 快捷键区（y=466 起）
        ky = 466
        cv.create_text(12, ky, text="快捷键（可输入键名改绑，如 F9 / HOME）",
                       anchor="w", fill=C_SUB, font=("Microsoft YaHei UI", 8))
        ky += 16
        self._apply_areas = {}
        self._key_feedback_areas = {}
        row_y = ky
        for uid in (1, 2, 3):
            op = OPS[uid][2]
            vk = self.app.hk.keys.get(uid)
            conflict = uid in self.app.hk.conflicts
            vk_name = key_name(vk) if vk is not None else "—"
            c = C_RED if conflict else C_GREEN
            cv.create_text(16, row_y + 15, text=op, anchor="w",
                           fill=C_TEXT, font=("Microsoft YaHei UI", 10, "bold"))
            chip(cv, 66, row_y + 15, 58, vk_name, c)
            # Entry 输入框（预填当前键名；用户正在输入时不被每秒刷新覆盖）
            eid = "key_%d" % uid
            if eid not in self._key_entries:
                ent = tk.Entry(cv, width=11, bg="#11131F", fg=C_TEXT,
                               insertbackground=C_TEXT, relief="flat",
                               font=("Microsoft YaHei UI", 9),
                               highlightthickness=1,
                               highlightbackground=C_LINE,
                               highlightcolor=C_ACCENT)
                ent.insert(0, vk_name)
                self._key_entries[eid] = ent
            ent = self._key_entries[eid]
            if cv.focus_get() is not ent and ent.get() != vk_name:
                ent.delete(0, "end")
                ent.insert(0, vk_name)
            self.cv_ent = ent
            cv.create_window(136, row_y + 15, window=ent, height=26,
                             width=104)
            # 应用按钮
            ax1, ay1, ax2, ay2 = 246, row_y, 296, row_y + 30
            self._apply_areas[uid] = (ax1, ay1, ax2, ay2)
            round_rect(cv, ax1, ay1, ax2, ay2, 8, fill="#26324A",
                       tags=("apply_%d" % uid,))
            cv.create_text((ax1 + ax2) / 2, (ay1 + ay2) / 2, text="改键",
                           fill=C_TEXT, font=("Microsoft YaHei UI", 9, "bold"),
                           tags=("apply_%d" % uid,))
            cv.tag_bind("apply_%d" % uid, "<Button-1>",
                        lambda e, u=uid: self._apply_key(u))
            # 反馈文字
            fb_text, fb_color = self._key_feedback.get(uid, ("", C_SUB))
            cv.create_text(306, row_y + 15, text=fb_text, anchor="w",
                           fill=fb_color, font=("Microsoft YaHei UI", 8))
            row_y += 40

        # 诊断按钮（快捷键区右侧）
        dx = W - 106
        self._diag_area = (dx, ky + 40, dx + 82, ky + 70)
        round_rect(cv, dx, ky + 40, dx + 82, ky + 70, 8, fill="#26324A")
        cv.create_text(dx + 41, ky + 55, text="🔍 一键诊断", fill=C_TEXT,
                       font=("Microsoft YaHei UI", 9, "bold"))

        # 诊断结果
        dy = ky + 86
        if self._diag_result:
            okn = sum(1 for c in self._diag_result
                      if c["status"] in ("ok", "skip"))
            cv.create_text(W / 2, dy + 8,
                           text="诊断 %d/%d 项通过" %
                                (okn, len(self._diag_result)),
                           fill=C_GREEN if okn == len(self._diag_result)
                           else C_YELLOW,
                           font=("Microsoft YaHei UI", 9, "bold"))
            for i, c in enumerate(self._diag_result[:7]):
                mark = {"ok": "✓", "warn": "⚠", "fail": "✗",
                        "skip": "-"}.get(c["status"], "?")
                color = {"ok": C_GREEN, "warn": C_YELLOW, "fail": C_RED,
                         "skip": C_GRAY}.get(c["status"], C_GRAY)
                cv.create_text(30, dy + 24 + i * 16, anchor="w",
                               text="%s %s" % (mark, c["name"]), fill=color,
                               font=("Microsoft YaHei UI", 8, "bold"))
                detail = c.get("detail", "")
                cv.create_text(110, dy + 24 + i * 16, anchor="w",
                               text=detail[:30], fill=C_SUB,
                               font=("Microsoft YaHei UI", 8))

        # 日志区（诊断结果之后，避免重叠）
        ly = dy + 24 + 7 * 16 + 12
        cv.create_text(12, ly, text="日志（logs/testbar_*.jsonl）", anchor="w",
                       fill=C_SUB, font=("Microsoft YaHei UI", 8))
        cv.create_line(10, ly + 8, W - 10, ly + 8, fill=C_LINE, width=1)
        logs = self.app.logger.buffer[-5:]
        for i, rec in enumerate(logs):
            ts = rec["ts"][11:23]
            txt = "%s  %s  %s" % (ts, rec["action"],
                                  (rec.get("detail") or "")[:22])
            cv.create_text(12, ly + 22 + i * 17, text=txt, anchor="w",
                           fill=C_SUB, font=("Microsoft YaHei UI", 8))

    def _caps_label(self):
        cap = caps_state()
        if self.app.state == "TESTING":
            if cap:
                return "强制开启"
            if self.app.caps_enforced is None:
                return "强制中..."
            return "强制失败!"
        return "开启" if cap else "关闭"

    def update_state(self):
        self.draw()
        s = self.app.pm.snapshot()
        self.chart_console.update_data(s["console"])
        self.chart_target.update_data(s["target"])
        gpu_card = s.get("gpu_card") or {}
        vram_tot = gpu_card.get("mem_total", 0)
        self.chart_console.set_vram_total(vram_tot)
        self.chart_target.set_vram_total(vram_tot)
        self.app.target_ok = s["target_ok"]
        self.app.target_display = s["target_name"] or self.app.target_display


# ---------- 覆盖条 ----------
class TaskbarOverlay(tk.Toplevel):
    W, H = 520, 40

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.configure(bg="#010203")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#010203")
        tb = taskbar_rect()
        tx = tb[0] + tb[2] - self.W - 12
        ty = tb[1] + (tb[3] - self.H) // 2
        self.geometry("%dx%d+%d+%d" % (self.W, self.H, tx, ty))
        self.cv = tk.Canvas(self, width=self.W, height=self.H,
                            bg="#010203", highlightthickness=0)
        self.cv.pack()
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        st = STATE_META[self.app.state]
        round_rect(cv, 0, 0, self.W, self.H, 12, fill=C_BG1,
                   outline=C_LINE, width=1)
        cx, cy = 18, self.H / 2
        cv.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=st["color"],
                       outline="")
        cv.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="",
                       outline=st["color"], width=1)
        cv.create_text(36, cy, text=st["text"], anchor="w", fill=st["color"],
                       font=("Microsoft YaHei UI", 10, "bold"))
        kx = 140
        for uid, op in ((1, "启动"), (2, "暂停"), (3, "终止")):
            vk = self.app.hk.keys.get(uid)
            ok = uid not in self.app.hk.conflicts and vk is not None
            label = "%s %s" % (key_name(vk), op) if vk is not None else op
            chip(cv, kx, cy, 88, label, C_TEXT if ok else C_RED)
            kx += 98
        cv.create_text(self.W - 14, cy, text="⇪" if caps_state() else "⇪̸",
                       anchor="e",
                       fill=C_GREEN if caps_state() else C_SUB,
                       font=("Microsoft YaHei UI", 11))

    def update_state(self):
        self.draw()


# ---------- 应用主控 ----------
class TestBarApp:
    def __init__(self, root, show_panel=True):
        self.root = root
        self.state = "IDLE"
        self.caps_before = caps_state()
        self.caps_enforced = None      # None=强制进行中 / True=已达成 / False=失败
        self.logger = Logger(BASE_DIR)
        self.hk = HotkeyManager(None)
        self.hk.start()
        self.target_name = DEFAULT_TARGET
        self.target_display = DEFAULT_TARGET
        self.target_ok = False
        self.pm = perfmon.PerfMonitor(interval=1.0, points=90)
        self.pm.start()
        self._attach_default_target()
        self.overlay = TaskbarOverlay(self)
        self.panel = ControlPanel(self) if show_panel else None
        self._exit_timer = None
        self._conflict_shown = False
        self._caps_fail_count = 0
        self.log("启动", state=self.state, detail="测试控制台 v5")
        rem = remote_tools_running()
        if rem:
            self.log("远程软件检测", detail="检测到 %s：键盘注入可能被接管，"
                     "CapsLock 强制/热键可能不稳定" % ", ".join(rem))
        self.root.after(100, self._tick)
        self.root.after(2000, self._caps_watch)

    def _attach_default_target(self):
        pid = proc_running(self.target_name)
        if pid:
            self.pm.set_target(pid, self.target_name)
            self.target_ok = True
            self.target_display = self.target_name

    def log(self, action, state=None, detail=""):
        self.logger.log(action, state=state or self.state, detail=detail)
        if self.panel:
            self.panel.draw()

    def browse_target(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(
            title="选择目标测试程序", filetypes=[("程序", "*.exe"),
                                             ("全部", "*.*")])
        if not p:
            return
        name = os.path.basename(p)
        self.log("选择目标", detail=name)
        pid = proc_running(name)
        if pid:
            self.pm.set_target(pid, name)
            self.target_ok = True
            self.target_display = name
        else:
            try:
                os.startfile(p)
                time.sleep(2)
                pid = proc_running(name)
                if pid:
                    self.pm.set_target(pid, name)
                    self.target_ok = True
                    self.target_display = name
                else:
                    self.target_ok = False
                    self.target_display = name + "（未运行）"
            except Exception as e:
                self.target_ok = False
                self.target_display = name + "（启动失败）"
        self._refresh()

    # --- 状态 ---
    def start(self):
        if self.state in ("IDLE", "TERMINATED", "PAUSED"):
            self.state = "TESTING"
            self.log("开始", state="TESTING", detail="CapsLock 强制进行中")
            if self._exit_timer:
                self.root.after_cancel(self._exit_timer)
                self._exit_timer = None
            # force_caps 含长 sleep，必须放独立线程，避免冻结 UI
            threading.Thread(target=self._force_on_worker, daemon=True).start()
        self._refresh()

    def _force_on_worker(self):
        self.caps_before = caps_state()
        ok = force_caps(True)
        self.caps_enforced = ok
        self.root.after(0, lambda: self._caps_result(ok))

    def _caps_result(self, ok):
        if ok:
            self.log("CapsLock", state="TESTING", detail="强制开启成功")
            self._caps_fail_count = 0
        else:
            self.log("CapsLock", state="TESTING",
                     detail="强制开启失败（可能被远程控制软件接管键盘）")
        self._refresh()

    def pause(self):
        if self.state == "TESTING":
            self.state = "PAUSED"
            self.log("暂停", state="PAUSED")
        elif self.state == "PAUSED":
            self.state = "TESTING"
            self.log("继续", state="TESTING")
            threading.Thread(target=self._force_on_worker, daemon=True).start()
        self._refresh()

    def terminate(self):
        self.state = "TERMINATED"
        if self.caps_enforced:
            threading.Thread(target=self._restore_caps, daemon=True).start()
        self.log("终止", state="TERMINATED")
        self._refresh()

    def _restore_caps(self):
        force_caps(self.caps_before)
        self.caps_enforced = False

    def request_exit(self):
        self.log("退出", detail="用户关闭面板")
        self._shutdown()

    def run_diag(self):
        checks = diagnose.run_checks(target=self.target_name or None,
                                     click_xy=None)
        if self.panel:                      # 审计：panel 可能为 None（--no-panel）
            self.panel._diag_result = checks
        okn = sum(1 for c in checks if c["status"] in ("ok", "skip"))
        ev_path = os.path.join(self.logger.ev_dir,
                               "diag_%s.bmp" % time.strftime("%H%M%S"))
        gdi_screenshot(ev_path)
        self.log("诊断", detail="%d/%d 通过，证据 %s" %
                 (okn, len(checks), os.path.basename(ev_path)))
        self._refresh()

    def _refresh(self):
        self.overlay.update_state()
        if self.panel:
            self.panel.update_state()

    def _tick(self):
        for ev in self.hk.poll():
            kind = ev[0]
            if kind == "hotkey":
                uid = ev[1]
                if uid == 1:
                    self.log("热键", detail="启动键按下")
                    self.start()
                elif uid == 2:
                    self.log("热键", detail="暂停键按下")
                    self.pause()
                elif uid == 3:
                    self.log("热键", detail="终止键按下")
                    self.terminate()
                    self._exit_timer = self.root.after(1500, self._shutdown)
            elif kind == "conflict":
                if not self._conflict_shown:
                    self._conflict_shown = True
                    self.log("冲突", detail=", ".join(
                        "%s(%s)" % (OPS[u][2], key_name(v))
                        for u, v in self.hk.conflicts.items()))
                    # 自动处理：优先应用备选键，无备选则禁用冲突键（不弹窗）
                    for uid, vk in list(self.hk.conflicts.items()):
                        fb = OPS[uid][1]
                        if self.hk.probe(fb):
                            if self.hk.apply(uid, fb):
                                self.log("改键", detail="%s → %s（自动应用备选键）"
                                         % (OPS[uid][2], key_name(fb)))
                            else:
                                self.hk.drop_conflict(uid)
                                self.log("改键失败", detail="%s 备选键 %s 亦被占用"
                                         % (OPS[uid][2], key_name(fb)))
                        else:
                            self.hk.drop_conflict(uid)
                            self.log("强制继续", detail="禁用冲突键 %s"
                                     % key_name(vk))
                self._refresh()
        self.root.after(100, self._tick)

    def _caps_watch(self):
        """TESTING 状态下守护 CapsLock（每 2s）：被外部/远程软件关掉则 1s 后再确认并拉回。
        force_caps 在线程执行，不冻结 UI。"""
        if self.state == "TESTING" and self.caps_enforced:
            if not caps_state():
                self.root.after(1000, self._caps_confirm)
                return
        self.root.after(2000, self._caps_watch)

    def _caps_confirm(self):
        if caps_state():
            self.root.after(2000, self._caps_watch)
            return
        threading.Thread(target=self._caps_reinforce, daemon=True).start()
        self.root.after(2000, self._caps_watch)

    def _caps_reinforce(self):
        ok = force_caps(True)
        if ok:
            self._caps_fail_count = 0
            self.root.after(0, lambda: self.log("CapsLock 守护",
                             detail="被关闭后已重新开启"))
        else:
            self._caps_fail_count += 1
            if self._caps_fail_count >= 3:
                self._caps_fail_count = 0
                self.root.after(0, lambda: self.log(
                    "CapsLock 警告",
                    detail="连续 3 次无法开启（可能被远程控制软件接管键盘）"))
        self.root.after(0, self._refresh)

    def _shutdown(self):
        if self._exit_timer:
            self.root.after_cancel(self._exit_timer)
        self.hk.stop()
        self.pm.stop()
        self.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-panel", action="store_true")
    a = ap.parse_args()
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
    root = tk.Tk()
    root.withdraw()
    TestBarApp(root, show_panel=not a.no_panel)
    root.mainloop()


if __name__ == "__main__":
    main()
