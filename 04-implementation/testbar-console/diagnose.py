# -*- coding: utf-8 -*-
"""diagnose.py — 点击失效七步排查：焦点 → 遮挡 → 坐标 → 权限 → 时序 → 注入 → 环境。

每步返回 {name, status: ok|warn|fail, detail, advice}。
用法：
  python diagnose.py --target "CookieSync" --click 1280,720
"""
import argparse
import ctypes
import json
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetForegroundWindow.restype = wintypes.HWND
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.restype = ctypes.c_int


def _pid_of(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _proc_name(pid):
    """进程 exe 名（QueryFullProcessImageName，快，无子进程）。"""
    try:
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                         wintypes.DWORD]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p,
            ctypes.POINTER(wintypes.DWORD)]
        h = kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            n = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return buf.value.rsplit("\\", 1)[-1].lower()
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return ""


def _title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _rect(hwnd):
    class RECT(ctypes.Structure):
        _fields_ = [("l", wintypes.LONG), ("t", wintypes.LONG),
                    ("r", wintypes.LONG), ("b", wintypes.LONG)]
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.l, r.t, r.r, r.b)


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _integrity():
    """当前进程完整性级别（原生 Token API，不启动 whoami 外部进程）。"""
    try:
        from ctypes import wintypes as _wt
        advapi32 = ctypes.WinDLL("advapi32")
        advapi32.OpenProcessToken.restype = _wt.BOOL
        advapi32.OpenProcessToken.argtypes = [
            ctypes.c_void_p, _wt.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        advapi32.GetTokenInformation.restype = _wt.BOOL
        advapi32.GetTokenInformation.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, _wt.DWORD,
            ctypes.POINTER(_wt.DWORD)]
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

        TOKEN_QUERY = 0x0008
        TokenIntegrityLevel = 25
        h_proc = kernel32.GetCurrentProcess()   # (HANDLE)-1 伪句柄
        if not h_proc:
            return "未知"
        h_tok = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(h_proc, TOKEN_QUERY,
                                         ctypes.byref(h_tok)):
            kernel32.CloseHandle(h_proc)
            return "未知"
        # 先查所需长度
        need = _wt.DWORD(0)
        advapi32.GetTokenInformation(h_tok, TokenIntegrityLevel, None, 0,
                                     ctypes.byref(need))
        buf = ctypes.create_string_buffer(need.value or 64)
        if not advapi32.GetTokenInformation(
                h_tok, TokenIntegrityLevel, buf, len(buf),
                ctypes.byref(need)):
            kernel32.CloseHandle(h_proc)
            return "未知"
        # TOKEN_MANDATORY_LABEL = SID_AND_ATTRIBUTES { PSID; Attributes }
        # PSID 指针位于缓冲区 offset 0
        sid_ptr = ctypes.cast(
            ctypes.addressof(buf), ctypes.POINTER(ctypes.c_void_p))
        sid = ctypes.c_void_p(sid_ptr.contents.value)
        advapi32.ConvertSidToStringSidA.restype = _wt.BOOL
        advapi32.ConvertSidToStringSidA.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        ps = ctypes.c_void_p()
        if advapi32.ConvertSidToStringSidA(sid, ctypes.byref(ps)) and ps.value:
            s = ctypes.string_at(ps.value).decode("ascii", "ignore")
            kernel32.CloseHandle(h_proc)
            if s.endswith("-12288"):
                return "High（管理员）"
            if s.endswith("-8192"):
                return "Medium（标准）"
            if s.endswith("-4096"):
                return "Low"
            return "未知(%s)" % s
        kernel32.CloseHandle(h_proc)
        return "未知"
    except Exception:
        return "未知"


def _session_locked():
    try:
        WTS_CURRENT_SERVER_HANDLE = 0
        wtsapi = ctypes.WinDLL("wtsapi32")
        wtsapi.WTSQuerySessionInformationW.restype = wintypes.BOOL
        wtsapi.WTSQuerySessionInformationW.argtypes = [
            ctypes.c_void_p, wintypes.DWORD, ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
        # WTSInfoClass=4(WTSConnectState)
        p = ctypes.c_void_p()
        n = wintypes.DWORD()
        if wtsapi.WTSQuerySessionInformationW(
                None, WTS_CURRENT_SERVER_HANDLE, 4, ctypes.byref(p),
                ctypes.byref(n)) and p.value:
            state = ctypes.cast(p.value, ctypes.POINTER(wintypes.DWORD)).contents.value
            wtsapi.WTSFreeMemory(p)
            # WTS_CONNECTSTATE_CLASS: 0=Active 1=Connected 2=ConnectQuery 3=Shadow
            #   4=Disconnected 5=Idle 6=Listen 7=Reset 8=Down 9=Init
            # 审计修正：仅 Disconnected/Idle/Down 视为不可交互，Connected(1) 不算锁定
            return state in (4, 5, 8)
        return False
    except Exception:
        return False


def _find_target_hwnd(target_name):
    """按窗口标题/进程名找目标窗口句柄（快路径：QueryFullProcessImageName）。"""
    wins = []
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            t = _title(hwnd)
            pid = _pid_of(hwnd)
            if target_name.lower() in t.lower() or \
                    target_name.lower() in _proc_name(pid):
                wins.append(hwnd)
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                     wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return wins


def run_checks(target=None, click_xy=None):
    """按 焦点→遮挡→坐标→权限→时序→注入→环境 顺序排查。"""
    checks = []
    t0 = time.time()
    fg = user32.GetForegroundWindow()
    fg_title, fg_pid = _title(fg), _pid_of(fg)

    # 1 焦点
    if target:
        hits = _find_target_hwnd(target)
        if not hits:
            checks.append({"step": 1, "name": "焦点", "status": "fail",
                           "detail": "找不到目标窗口: %s" % target,
                           "advice": "确认程序已启动、窗口标题/进程名拼写正确"})
        else:
            target_hwnd = hits[0]
            in_fg = fg == target_hwnd or fg_pid == _pid_of(target_hwnd)
            checks.append({"step": 1, "name": "焦点", "status":
                           "ok" if in_fg else "warn",
                           "detail": "前台=%s(%s) 目标=%s(%s)" % (
                               fg_title[:24], fg_pid,
                               _title(target_hwnd)[:24], _pid_of(target_hwnd)),
                           "advice": "目标不在前台 → 先 activate 目标窗口再点击" if
                           not in_fg else ""})
    else:
        checks.append({"step": 1, "name": "焦点", "status": "ok",
                       "detail": "前台=%s" % fg_title[:40], "advice": ""})

    # 2 遮挡
    if click_xy:
        x, y = click_xy
        pt = wintypes.POINT(x, y)
        top = user32.WindowFromPoint(pt)
        top_title = _title(top)
        # 目标窗口若已找到：顶层窗口与目标同 hwnd/同 pid 视为无遮挡
        target_hwnd = None
        if target:
            hits = _find_target_hwnd(target)
            if hits:
                target_hwnd = hits[0]
        blocked = (target_hwnd is None and top) or \
                  (target_hwnd is not None and top and
                   top != target_hwnd and _pid_of(top) != _pid_of(target_hwnd))
        checks.append({"step": 2, "name": "遮挡", "status":
                       "fail" if blocked else "ok",
                       "detail": "点击点(%d,%d)顶层窗口=%s" % (
                           x, y, top_title[:30] or "(桌面)"),
                       "advice": "有窗口盖住目标 → 先置顶/关闭遮挡窗口" if
                       blocked else ""})
    else:
        checks.append({"step": 2, "name": "遮挡", "status": "skip",
                       "detail": "未提供点击坐标", "advice": ""})

    # 3 坐标
    if click_xy and target:
        hits = _find_target_hwnd(target)
        if hits:
            r = _rect(hits[0])
            inside = r[0] <= x <= r[2] and r[1] <= y <= r[3]
            checks.append({"step": 3, "name": "坐标", "status":
                           "ok" if inside else "warn",
                           "detail": "目标rect=%s 点击点%s" % (
                               list(r), "在内部" if inside else "在外部"),
                           "advice": "点击点在窗口外 → 用 locate.py 重新定位" if
                           not inside else ""})
        else:
            checks.append({"step": 3, "name": "坐标", "status": "skip",
                           "detail": "目标未找到", "advice": ""})
    else:
        checks.append({"step": 3, "name": "坐标", "status": "skip",
                       "detail": "未提供目标/坐标", "advice": ""})

    # 4 权限
    admin = _is_admin()
    integ = _integrity()
    checks.append({"step": 4, "name": "权限", "status":
                   "ok" if admin else "warn",
                   "detail": "管理员=%s 完整性=%s" % (admin, integ),
                   "advice": "目标程序以管理员运行而本进程非管理员时，"
                             "注入会被 UIPI 拦截 → 用管理员方式启动 testbar" if
                   not admin else ""})

    # 5 时序
    checks.append({"step": 5, "name": "时序", "status": "ok",
                   "detail": "本次检查耗时 %.0fms（>2000ms 视为卡顿）" %
                   ((time.time() - t0) * 1000),
                   "advice": "点击后立刻截图验证（verify 阶段），不通过则"
                             "等待后重试"})

    # 6 注入（UIPI：高完整性进程的窗口拒绝低完整性进程注入）
    integ_ok = "High（管理员）" in integ or admin
    checks.append({"step": 6, "name": "注入", "status":
                   "ok" if integ_ok else "warn",
                   "detail": "当前完整性=%s（UIPI 拦截条件是目标完整性更高）"
                             % integ,
                   "advice": "目标程序以管理员运行而本进程非管理员时，"
                             "SendInput 会被 UIPI 静默拦截 → 管理员启动 testbar" if
                   not integ_ok else ""})

    # 7 环境
    locked = _session_locked()
    gdi32 = ctypes.windll.gdi32
    dc = user32.GetDC(0)
    cx = gdi32.GetDeviceCaps(dc, 8)   # HORZRES 物理
    cy = gdi32.GetDeviceCaps(dc, 10)  # VERTRES
    user32.ReleaseDC(0, dc)
    checks.append({"step": 7, "name": "环境", "status":
                   "fail" if locked else "ok",
                   "detail": "会话锁定=%s 屏幕=%dx%d" % (locked, cx, cy),
                   "advice": "屏幕已锁/切到安全桌面 → 解锁后重试" if locked
                   else ""})

    return checks


def main():
    # DPI 感知：物理像素（否则 GetDeviceCaps 返回逻辑分辨率）
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=None)
    ap.add_argument("--click", default=None)
    a = ap.parse_args()
    xy = tuple(int(v) for v in a.click.split(",")) if a.click else None
    checks = run_checks(a.target, xy)
    print(json.dumps(checks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
