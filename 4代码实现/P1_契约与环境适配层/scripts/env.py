# -*- coding: utf-8 -*-
"""env.py — UI 自动化环境层：DPI 感知、多屏几何、进程/端口、窗口枚举。

统一坐标契约：
- 所有屏幕坐标一律使用"物理像素"（与 mss/截图/CopyFromScreen 一致）。
- DPI 感知必须在进程最早期调用（SetProcessDpiAwarenessContext），否则 GetWindowRect
  返回的是虚拟化坐标，与截图错位。
"""
import ctypes
import ctypes.wintypes
import os
import json
import subprocess
import re
import time

# ---------- DPI 感知（必须在任何窗口/截图 API 之前调用） ----------
_DPI_AWARE_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

# ---------- 噪声窗口过滤（感知层候选剔除） ----------
NOISE_TITLES = ("豆包", "任务管理器", "Program Manager", "Windows 输入体验",
                "开始", "搜索", "桌面", "Shell_TrayWnd")
NOISE_CLASSES = ("Shell_TrayWnd", "Progman", "WorkerW",
                 "Windows.UI.Core.CoreWindow", "LDRemoteOpNotifyBar",
                 "ThumbnailDeviceHelperWnd", "EdgeUiInputTopWndClass")

_find_windows_cache = None


def set_dpi_awareness():
    """设置 Per-Monitor V2 DPI 感知。失败则回退 System Aware。幂等。"""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(
            _DPI_AWARE_CONTEXT_PER_MONITOR_AWARE_V2)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def dpi_for_window(hwnd=None):
    """取窗口真实 DPI 与缩放比。无窗口时取系统 DPI。"""
    try:
        if hwnd:
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        else:
            dpi = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    return int(dpi), dpi / 96.0


# ---------- 多屏几何 ----------
class MonitorInfo(object):
    def __init__(self, left, top, right, bottom, is_primary, name):
        self.left, self.top = left, top
        self.right, self.bottom = right, bottom
        self.width = right - left
        self.height = bottom - top
        self.is_primary = is_primary
        self.name = name

    def to_dict(self):
        return {"left": self.left, "top": self.top, "right": self.right,
                "bottom": self.bottom, "width": self.width, "height": self.height,
                "primary": self.is_primary, "name": self.name}


def _monitor_enum():
    monitors = []

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32),
                    ("rcMonitor", ctypes.c_long * 4),
                    ("rcWork", ctypes.c_long * 4),
                    ("dwFlags", ctypes.c_uint32),
                    ("szDevice", ctypes.c_wchar * 32)]

    def cb(hmon, hdc, lprc, lparam):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        rc = mi.rcMonitor
        monitors.append(MonitorInfo(rc[0], rc[1], rc[2], rc[3],
                                    bool(mi.dwFlags & 1), mi.szDevice))
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
                                         ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_void_p)
    ctypes.windll.user32.EnumDisplayMonitors(None, None,
                                             MONITORENUMPROC(cb), 0)
    return monitors


def monitors():
    return _monitor_enum()


def primary_monitor():
    for m in _monitor_enum():
        if m.is_primary:
            return m
    return _monitor_enum()[0]


# ---------- 窗口枚举 / 几何 ----------
def find_windows(title_match=None, class_match=None, visible_only=True,
                 pid=None, cache_ttl=0.5):
    """按标题/类名子串/进程号枚举顶层窗口，返回 [{hwnd,title,class,rect,pid}]。
    pid: 非 None 时仅返回该进程的窗口；cache_ttl>0 时结果缓存 cache_ttl 秒。"""
    global _find_windows_cache
    key = (title_match, class_match, visible_only, pid)
    now = time.time()
    if cache_ttl > 0 and _find_windows_cache \
            and _find_windows_cache["args"] == key \
            and now - _find_windows_cache["t"] < cache_ttl:
        return _find_windows_cache["result"]
    out = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                         ctypes.c_void_p)

    def cb(hwnd, lparam):
        if visible_only and not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 1024)
        title = buf.value
        cls = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, cls, 256)
        class_name = cls.value
        if title_match and title_match not in title:
            return True
        if class_match and class_match not in class_name:
            return True
        if pid is not None:
            p = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd, ctypes.byref(p))
            if int(p.value) != pid:
                return True
        r = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
        p = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(
            hwnd, ctypes.byref(p))
        out.append({"hwnd": int(hwnd), "title": title, "class": class_name,
                    "rect": [r.left, r.top, r.right, r.bottom],
                    "pid": int(p.value)})
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(cb), 0)
    if cache_ttl > 0:
        _find_windows_cache = {"t": time.time(), "args": key, "result": out}
    return out


def find_children(hwnd, class_match=None):
    """枚举子窗口（控件），返回 [{hwnd,class,text,rect}]。"""
    out = []
    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                       ctypes.c_void_p)

    def cb(child, lparam):
        cls = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(child, cls, 256)
        class_name = cls.value
        if class_match and class_match not in class_name:
            return True
        txt = ctypes.create_unicode_buffer(1024)
        ctypes.windll.user32.GetWindowTextW(child, txt, 1024)
        r = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(child, ctypes.byref(r))
        out.append({"hwnd": int(child), "class": class_name,
                    "text": txt.value, "rect": [r.left, r.top, r.right, r.bottom]})
        return True

    ctypes.windll.user32.EnumChildWindows(hwnd, EnumChildProc(cb), 0)
    return out


def window_rect(hwnd):
    r = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right, r.bottom]


def activate_window(hwnd):
    """激活窗口：ShowWindow + AttachThreadInput + SetForegroundWindow。"""
    try:
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        fg = ctypes.windll.user32.GetForegroundWindow()
        cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(fg, None)
        target_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        if fg_tid != cur_tid:
            ctypes.windll.user32.AttachThreadInput(cur_tid, fg_tid, True)
        if target_tid != cur_tid:
            ctypes.windll.user32.AttachThreadInput(cur_tid, target_tid, True)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        if fg_tid != cur_tid:
            ctypes.windll.user32.AttachThreadInput(cur_tid, fg_tid, False)
        if target_tid != cur_tid:
            ctypes.windll.user32.AttachThreadInput(cur_tid, target_tid, False)
        return True
    except Exception:
        return False


# ---------- 感知层：按规则自选目标（确定性，不靠 LLM 猜） ----------
def pick_target(rules, windows=None):
    """感知层自动选定目标窗口，输出确定性 target_hwnd + 依据。

    rules: 规则列表，每项 {title/class/proc: 子串, exclude_noise: bool}
           未给 rules 时只用 exclude_noise 过滤（此时仍给出候选排序，
           但 target 只在规则命中时输出——避免瞎猜）。
    返回 {"target": {hwnd,title,class,rect,pid,reason,score} | None,
          "candidates": [...], "rule_hits": [...]}
    """
    rules = rules or []
    wins = windows if windows is not None \
        else find_windows(visible_only=True)

    def noise(w):
        t = w["title"]
        c = w["class"]
        for k in NOISE_TITLES:
            if k and k in t:
                return True
        for k in NOISE_CLASSES:
            if k and k in c:
                return True
        return not t.strip()

    clean = [w for w in wins if not noise(w)]
    scored = []
    for w in clean:
        score = 0
        reason = []
        for rule in rules:
            s = 0
            if rule.get("title") and rule["title"] in w["title"]:
                s += 10
            if rule.get("class") and rule["class"] in w["class"]:
                s += 5
            if rule.get("proc"):
                try:
                    import psutil
                    if rule["proc"].lower() in \
                            psutil.Process(w["pid"]).name().lower():
                        s += 5
                except Exception:
                    pass
            if s:
                reason.append(str(rule.get("name") or rule))
                score += s
        scored.append({"hwnd": w["hwnd"], "title": w["title"],
                       "class": w["class"], "rect": w["rect"],
                       "pid": w["pid"], "score": score,
                       "reason": ",".join(reason)})
    scored.sort(key=lambda x: -x["score"])
    target = scored[0] if (scored and scored[0]["score"] > 0) else None
    return {
        "target": target,
        "candidates": [c for c in scored if c["score"] > 0],
        "rule_hits": scored[:10],
    }


def window_from_point(x, y):
    """取 (x,y) 处的顶层窗口（含其所属进程 pid），用于点击前遮挡检查。"""
    hwnd = ctypes.windll.user32.WindowFromPoint(
        ctypes.wintypes.POINT(x, y))
    if not hwnd:
        return None
    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(
        hwnd, ctypes.byref(pid))
    r = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
    return {"hwnd": int(hwnd), "pid": int(pid.value),
            "title": buf.value,
            "rect": [r.left, r.top, r.right, r.bottom]}


def wait_window_ready(hwnd, timeout=5.0):
    """轮询窗口是否响应（SendMessageTimeout WM_NULL，0xFFFF），失败返回 False。"""
    WM_NULL = 0
    SMTO_ABORTIFHUNG = 2
    t0 = time.time()
    while time.time() - t0 < timeout:
        res = ctypes.c_long()  # LRESULT 等价 c_long（wintypes 无 LRESULT，修复自审计）
        r = ctypes.windll.user32.SendMessageTimeoutW(
            hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, 200,
            ctypes.byref(res))
        if r:
            return True
        time.sleep(0.1)
    return False


# ---------- 进程 / 端口 ----------
def kill_process(name):
    """杀进程树，返回是否成功。name 如 'chrome.exe'。"""
    try:
        subprocess.run(["taskkill", "/f", "/im", name, "/t"],
                       capture_output=True, timeout=15)
        return True
    except Exception:
        return False


def process_count(name):
    try:
        import psutil
        return sum(1 for p in psutil.process_iter(["name"])
                   if (p.info.get("name") or "").lower() == name.lower())
    except Exception:
        return 0


def port_listen(port, timeout=3):
    """检查 TCP 端口是否在监听，返回 True/False。psutil 主 + socket 兜底。"""
    try:
        import psutil
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port \
                    and c.status == "LISTEN":
                return True
    except Exception:
        pass
    try:
        import socket
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def wait_port(port, timeout=20.0, interval=0.5):
    """轮询等待端口监听，成功返回 True。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if port_listen(port):
            return True
        time.sleep(interval)
    return port_listen(port)


def http_json(url, timeout=4):
    """GET JSON，失败返回 None。"""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


if __name__ == "__main__":
    set_dpi_awareness()
    dpi, scale = dpi_for_window()
    print(json.dumps({
        "dpi": dpi, "scale": scale,
        "monitors": [m.to_dict() for m in monitors()],
        "windows": find_windows(title_match="", visible_only=True)[:5]
    }, ensure_ascii=False, indent=2))
