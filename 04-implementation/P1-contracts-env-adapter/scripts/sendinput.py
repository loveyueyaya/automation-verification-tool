# -*- coding: utf-8 -*-
"""sendinput.py — 真实输入层：SendInput 注入 + 剪贴板粘贴 + 句柄消息直投。

坐标契约：默认物理像素（2560x1440 真实分辨率），也可用 --pct 千分比。
设计原则：
  - 中文/长路径一律剪贴板粘贴（IME 无关，最可靠）
  - 控件焦点不可控时，用句柄消息直投（WM_KEYDOWN/WM_CHAR），不依赖前台焦点
  - 激活窗口用 env.activate_window（AttachThreadInput + SetForegroundWindow）

用法：
  python sendinput.py click 1280 720            # 物理像素单击
  python sendinput.py click 500 500 --pct       # 千分比单击
  python sendinput.py dblclick 1280 720         # 双击（两次 click，间隔双击阈值内）
  python sendinput.py type "hello"              # ASCII 键入
  python sendinput.py key 13                    # VK 键
  python sendinput.py hotkey 0x11,0x41          # Ctrl+A
  python sendinput.py clip "中文内容"            # 进剪贴板
  python sendinput.py paste 1280 720            # 点坐标 + Ctrl+V
  python sendinput.py msg 123456 0x0D           # 向句柄发 WM_KEYDOWN(回车)
"""
import argparse
import ctypes
import ctypes.wintypes as wintypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

env.set_dpi_awareness()

# ---------- SendInput 结构 ----------
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


def _send_input(*inps):
    arr = (INPUT * len(inps))(*inps)
    return ctypes.windll.user32.SendInput(len(inps), arr, ctypes.sizeof(INPUT))


def _mouse_input(flags, x=None, y=None):
    mi = MOUSEINPUT()
    if x is not None and y is not None:
        # 绝对坐标：0-65535 归一化到虚拟桌面
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        mi.dx = int(x * 65535 / max(sw, 1))
        mi.dy = int(y * 65535 / max(sh, 1))
        mi.dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK | flags
    else:
        mi.dwFlags = flags
    return INPUT(INPUT_MOUSE, INPUTUNION(mi=mi))


def _key_input(vk, up=False, unicode_char=None):
    ki = KEYBDINPUT()
    if unicode_char is not None:
        ki.wScan = ord(unicode_char)
        ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    else:
        ki.wVk = vk
        ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    return INPUT(INPUT_KEYBOARD, INPUTUNION(ki=ki))


def move(x, y):
    _send_input(_mouse_input(MOUSEEVENTF_MOVE, x, y))


def click(x, y, dbl=False):
    flags_down = MOUSEEVENTF_LEFTDOWN
    flags_up = MOUSEEVENTF_LEFTUP
    if dbl:
        # 两次 click，间隔 60ms（在双击检测阈值内）
        for _ in range(2):
            _send_input(_mouse_input(flags_down, x, y))
            time.sleep(0.02)
            _send_input(_mouse_input(flags_up, x, y))
            time.sleep(0.06)
    else:
        _send_input(_mouse_input(flags_down, x, y))
        time.sleep(0.02)
        _send_input(_mouse_input(flags_up, x, y))


def key(vk, hold=0.03):
    _send_input(_key_input(vk))
    time.sleep(hold)
    _send_input(_key_input(vk, up=True))


def type_ascii(text):
    for ch in text:
        if ch.isupper():
            _send_input(_key_input(0x10))  # shift down
            time.sleep(0.01)
        vk = ord(ch.upper())
        _send_input(_key_input(vk))
        time.sleep(0.01)
        _send_input(_key_input(vk, up=True))
        if ch.isupper():
            _send_input(_key_input(0x10, up=True))
        time.sleep(0.01)


def hotkey(vks):
    for v in vks:
        _send_input(_key_input(v))
        time.sleep(0.02)
    for v in reversed(vks):
        _send_input(_key_input(v, up=True))
        time.sleep(0.02)


def to_clipboard(text):
    """写入剪贴板（Unicode）。失败自动重试 3 次（剪贴板可能被占用）。"""
    CF_UNICODETEXT = 13
    # 显式设置指针型返回（windll 默认截断为 32 位，句柄会错）
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
    user32 = ctypes.windll.user32
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    data = (text + "\x00").encode("utf-16-le")
    for attempt in range(3):
        if not user32.OpenClipboard(0):
            time.sleep(0.15)
            continue
        try:
            user32.EmptyClipboard()
            h = kernel32.GlobalAlloc(0x0042, len(data))
            if not h:
                raise RuntimeError("GlobalAlloc 失败")
            p = kernel32.GlobalLock(h)
            if not p:
                raise RuntimeError("GlobalLock 失败")
            ctypes.memmove(ctypes.c_void_p(p), data, len(data))
            kernel32.GlobalUnlock(h)
            if not user32.SetClipboardData(CF_UNICODETEXT, h):
                raise RuntimeError("SetClipboardData 失败")
            return True
        finally:
            user32.CloseClipboard()
    raise RuntimeError("剪贴板写入失败（3 次重试）")


def paste_at(x, y, text):
    """定位+粘贴中文（点坐标 → Ctrl+A → Ctrl+V）。"""
    click(x, y)
    time.sleep(0.15)
    hotkey([0x11, 0x41])
    time.sleep(0.1)
    hotkey([0x11, 0x56])
    time.sleep(0.1)


# ---------- 句柄消息直投（不依赖前台焦点） ----------
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202


def post_key(hwnd, vk, repeat=1):
    """向指定窗口句柄直投按键（解决焦点被抢时键盘失效）。"""
    for _ in range(repeat):
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)
        time.sleep(0.02)


def post_char(hwnd, ch):
    """向指定句柄直投 Unicode 字符（解决中文 type 失败）。"""
    ctypes.windll.user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["click", "dblclick", "move", "type",
                                    "key", "hotkey", "clip", "paste", "msg",
                                    "msgchar"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--pct", action="store_true", help="坐标用千分比")
    a = ap.parse_args()

    def P(x, y):
        if a.pct:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            return int(x * sw / 1000), int(y * sh / 1000)
        return int(x), int(y)

    if a.cmd in ("click", "dblclick", "move"):
        x, y = P(int(a.args[0]), int(a.args[1]))
        if a.cmd == "click":
            click(x, y)
        elif a.cmd == "dblclick":
            click(x, y, dbl=True)
        else:
            move(x, y)
    elif a.cmd == "type":
        type_ascii(a.args[0])
    elif a.cmd == "key":
        key(int(a.args[0], 0))
    elif a.cmd == "hotkey":
        hotkey([int(v, 0) for v in a.args[0].split(",")])
    elif a.cmd == "clip":
        to_clipboard(" ".join(a.args))
    elif a.cmd == "paste":
        x, y = P(int(a.args[0]), int(a.args[1]))
        paste_at(x, y, "")
    elif a.cmd == "msg":
        hwnd = int(a.args[0])
        vk = int(a.args[1], 0)
        post_key(hwnd, vk)
    elif a.cmd == "msgchar":
        hwnd = int(a.args[0])
        post_char(hwnd, a.args[1])
    print("ok")


if __name__ == "__main__":
    main()
