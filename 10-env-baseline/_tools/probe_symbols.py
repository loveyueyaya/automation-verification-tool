# -*- coding: utf-8 -*-
"""深挖：kernel32/user32/gdi32 若干符号的解析差异（windll vs WinDLL），并给出 GetProcAddress 原始结果。"""
import ctypes
import ctypes.wintypes as wt
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NAMES = {
    "kernel32": ["GlobalAlloc", "GlobalLock", "GlobalSize", "GlobalUnlock", "GetCurrentProcess",
                 "GetCurrentThreadId", "CloseHandle", "GetConsoleWindow", "OpenProcess"],
    "user32": ["GetDC", "ReleaseDC", "GetWindowDC", "GetSystemMetrics", "GetForegroundWindow",
               "OpenClipboard", "CloseClipboard", "EmptyClipboard", "SetClipboardData"],
    "gdi32": ["BitBlt", "CreateCompatibleDC", "CreateCompatibleBitmap", "GetDeviceCaps",
              "SelectObject", "DeleteDC", "DeleteObject"],
}

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
g32 = ctypes.WinDLL("gdi32", use_last_error=True)

print("{:10} {:26} {:>14} {:>14} {:>10}".format("DLL", "Symbol", "WinDLL(新)", "windll(缓存)", "GetProcAddr"))
print("-" * 82)
dlls = {"kernel32": (k32, ctypes.windll.kernel32), "user32": (u32, ctypes.windll.user32),
        "gdi32": (g32, ctypes.windll.gdi32)}
for dname, names in NAMES.items():
    fresh, cached = dlls[dname]
    for nm in names:
        try:
            getattr(fresh, nm)
            a = "OK"
        except AttributeError:
            a = "缺失"
        try:
            getattr(cached, nm)
            b = "OK"
        except AttributeError:
            b = "缺失"
        ctypes.set_last_error(0)
        gpa = ctypes.windll.kernel32.GetProcAddress
        gpa.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        gpa.restype = ctypes.c_void_p
        h = gpa(ctypes.c_void_p(fresh._handle), nm.encode())
        err = ctypes.get_last_error()
        c = "句柄=%s" % (h if h else "NULL(err=%d)" % err)
        flag = "  ⚠" if (a == "缺失" or b == "缺失") else ""
        print("{:10} {:26} {:>14} {:>14} {:>10}{}".format(dname, nm, a, b, c, flag))

print("\n=== 结论判定 ===")
print("若 WinDLL(新) 为 OK 而 windll(缓存) 为缺失 → 属 ctypes 缓存/加载差异，项目用 WinDLL 不受影响")
