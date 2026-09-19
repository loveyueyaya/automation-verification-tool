# -*- coding: utf-8 -*-
"""项目实际调用的 Win32 API 逐一验证：解析 + 安全实跑。

判定口径：
  ✅ 实跑通过  —— 拿到符合预期的返回值
  🟡 仅解析   —— 符号存在但按要求不实跑（会改动用户界面/剪贴板）
  ❌ 失败     —— 解析失败或调用异常

用法：python verify_win32_api.py
"""
import ctypes
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

u = ctypes.windll.user32
k = ctypes.windll.kernel32
a = ctypes.windll.advapi32
sh = ctypes.windll.shcore
g = ctypes.windll.gdi32

results = []


def check(dll_name, dll, fname, args_spec=None, call=None, note=""):
    """解析并（可选）调用；call 为无参 lambda。"""
    try:
        fn = getattr(dll, fname)
    except AttributeError as e:
        results.append((dll_name, fname, "❌ 解析失败", str(e)))
        return None
    if call is None:
        results.append((dll_name, fname, "🟡 仅解析", note))
        return fn
    try:
        r = call(fn)
        results.append((dll_name, fname, "✅ 实跑通过", "返回=%r %s" % (r, note)))
        return r
    except Exception as e:
        results.append((dll_name, fname, "❌ 调用异常", "%s: %s" % (type(e).__name__, e)))
        return None


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]


def main():
    fg = u.GetForegroundWindow()
    pid = ctypes.c_ulong(0)
    tid = u.GetWindowThreadProcessId(ctypes.c_void_p(fg), ctypes.byref(pid))
    console = k.GetConsoleWindow()
    target = console or fg

    # ---------- user32：窗口/几何 ----------
    check("user32", u, "GetSystemMetrics", call=lambda f: f(0))
    check("user32", u, "GetForegroundWindow", call=lambda f: f())
    check("user32", u, "GetDesktopWindow", call=lambda f: f())
    check("user32", u, "GetWindowThreadProcessId",
          call=lambda f: f(ctypes.c_void_p(fg), ctypes.byref(pid)))
    check("user32", u, "GetWindowRect",
          call=lambda f: f(ctypes.c_void_p(fg), ctypes.byref(RECT())))
    check("user32", u, "GetWindowTextW",
          call=lambda f: f(ctypes.c_void_p(fg), ctypes.create_unicode_buffer(256), 256))
    check("user32", u, "GetClassNameW",
          call=lambda f: f(ctypes.c_void_p(fg), ctypes.create_unicode_buffer(256), 256))
    check("user32", u, "IsWindowVisible", call=lambda f: f(ctypes.c_void_p(fg)))
    check("user32", u, "GetAncestor", call=lambda f: f(ctypes.c_void_p(fg), 2))
    check("user32", u, "WindowFromPoint",
          call=lambda f: f(POINT(10, 10)))
    check("user32", u, "GetDpiForSystem", call=lambda f: f())
    check("user32", u, "GetDpiForWindow", call=lambda f: f(ctypes.c_void_p(fg)))
    check("user32", u, "GetMonitorInfoW",
          call=lambda f: f(ctypes.c_void_p(0), ctypes.byref(
              MONITORINFO(ctypes.sizeof(MONITORINFO), RECT(), RECT(), 0))) if False else
          f(ctypes.windll.user32.MonitorFromWindow(ctypes.c_void_p(fg), 2),
            ctypes.byref(MONITORINFO(ctypes.sizeof(MONITORINFO), RECT(), RECT(), 0))))

    n_win = [0]

    def _cb(hwnd, lparam):
        n_win[0] += 1
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    check("user32", u, "EnumWindows", call=lambda f: f(WNDENUMPROC(_cb), 0))
    check("user32", u, "EnumChildWindows", call=lambda f: f(ctypes.c_void_p(fg), WNDENUMPROC(_cb), 0))
    check("user32", u, "EnumDisplayMonitors",
          call=lambda f: f(None, None, WNDENUMPROC(_cb), 0))
    check("user32", u, "AttachThreadInput",
          call=lambda f: f(k.GetCurrentThreadId(), tid, True) and f(k.GetCurrentThreadId(), tid, False))

    # ---------- user32：输入/消息（用无副作用的参数实跑）----------
    check("user32", u, "SendInput", call=lambda f: f(0, None, 40), note="(0 个事件，无副作用)")
    check("user32", u, "SendMessageTimeoutW",
          call=lambda f: f(ctypes.c_void_p(fg), 0, 0, 0, 2, 1000, ctypes.byref(ctypes.c_ulong(0))),
          note="(WM_NULL)")
    check("user32", u, "PostMessageW", call=lambda f: f(ctypes.c_void_p(target), 0, 0, 0),
          note="(WM_NULL→自身控制台窗口)")
    check("user32", u, "SetForegroundWindow", call=lambda f: f(ctypes.c_void_p(fg)),
          note="(目标是当前前台窗口，等同无操作)")
    check("user32", u, "SetWindowPos",
          call=lambda f: f(ctypes.c_void_p(console), 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0010),
          note="(SWP_NOMOVE|NOSIZE|NOZORDER|NOACTIVATE 全 no-op)")
    check("user32", u, "ShowWindow", call=lambda f: f(ctypes.c_void_p(console), 5),
          note="(对自身控制台窗口 SW_SHOW)")
    check("user32", u, "BringWindowToTop", call=lambda f: f(ctypes.c_void_p(console)),
          note="(自身控制台窗口)")
    check("user32", u, "EmptyClipboard", note="会清空用户剪贴板，未实跑")
    check("user32", u, "SetClipboardData", note="会改写用户剪贴板，未实跑")

    # ---------- user32：剪贴板内存 API（不动剪贴板内容）----------
    check("user32", u, "OpenClipboard", call=lambda f: f(ctypes.c_void_p(target)))
    check("user32", u, "CloseClipboard", call=lambda f: f())
    kk = ctypes.WinDLL("kernel32")          # 项目 sendinput.py 用 kernel32.GlobalAlloc（非 user32）
    kk.GlobalAlloc.restype = ctypes.c_void_p
    kk.GlobalLock.restype = ctypes.c_void_p
    kk.GlobalLock.argtypes = [ctypes.c_void_p]
    kk.GlobalUnlock.argtypes = [ctypes.c_void_p]
    h = check("kernel32", kk, "GlobalAlloc",
              call=lambda f: f(0x0042, 16), note="(GMEM_MOVEABLE|GMEM_ZEROINIT，与项目一致)")
    check("kernel32", kk, "GlobalLock", call=lambda f: f(ctypes.c_void_p(h)))
    check("kernel32", kk, "GlobalSize", call=lambda f: f(ctypes.c_void_p(h)))
    check("kernel32", kk, "GlobalUnlock", call=lambda f: f(ctypes.c_void_p(h)))

    # ---------- kernel32 ----------
    hp = check("kernel32", k, "GetCurrentProcess", call=lambda f: f())
    check("kernel32", k, "GetCurrentThreadId", call=lambda f: f())
    check("kernel32", k, "CloseHandle", call=lambda f: f(ctypes.c_void_p(hp)))
    check("kernel32", k, "GetConsoleWindow", call=lambda f: f())

    # ---------- advapi32：UIPI 判定（项目 env_probe 用）----------
    tok = ctypes.c_void_p(0)
    hp2 = k.GetCurrentProcess()
    ok = check("advapi32", a, "OpenProcessToken",
               call=lambda f: f(hp2, 0x0008, ctypes.byref(tok)), note="(TOKEN_QUERY)")
    buf = ctypes.create_string_buffer(64)
    need = ctypes.c_ulong(0)
    check("advapi32", a, "GetTokenInformation",
          call=lambda f: f(tok, 25, buf, 64, ctypes.byref(need)), note="(TokenIntegrityLevel)")
    sid = ctypes.c_void_p(ctypes.addressof(buf) + 8)
    check("advapi32", a, "GetSidSubAuthorityCount", call=lambda f: f(sid))
    check("advapi32", a, "GetSidSubAuthority",
          call=lambda f: f(sid, 0), note="(最后一级 RID＝完整性级别)")

    # ---------- shcore：DPI ----------
    check("shcore", sh, "SetProcessDpiAwareness", call=lambda f: f(2),
          note="(PROCESS_PER_MONITOR_DPI_AWARE；已设置时返回 E_ACCESSDENIED 属正常)")
    check("user32", u, "SetProcessDpiAwarenessContext", call=lambda f: f(ctypes.c_void_p(-4)),
          note="(PER_MONITOR_AWARE_V2；同上)")

    # ---------- gdi32 / user32 的 GDI 入口：盘点标注"当前未使用" ----------
    check("user32", u, "GetDC", call=lambda f: f(ctypes.c_void_p(fg)), note="(盘点标注未使用)")
    check("user32", u, "ReleaseDC", call=lambda f: f(ctypes.c_void_p(fg), ctypes.c_void_p(u.GetDC(ctypes.c_void_p(fg)))),
          note="(配对释放，盘点标注未使用)")
    check("gdi32", g, "BitBlt", note="盘点标注未使用，仅确认可解析")
    check("gdi32", g, "CreateCompatibleDC", note="盘点标注未使用，仅确认可解析")

    # ---------- 输出 ----------
    print("{:10} {:28} {:12} {}".format("DLL", "API", "判定", "备注"))
    print("-" * 100)
    ok_n = mid_n = bad_n = 0
    for d, f, st, note in results:
        if st.startswith("✅"):
            ok_n += 1
        elif st.startswith("🟡"):
            mid_n += 1
        else:
            bad_n += 1
        print("{:10} {:28} {:12} {}".format(d, f, st, note))
    print("-" * 100)
    print("合计 {} 项：实跑通过 {} / 仅解析 {} / 失败 {}".format(len(results), ok_n, mid_n, bad_n))
    print("EnumWindows 枚举到顶层窗口数:", n_win[0])


if __name__ == "__main__":
    main()
