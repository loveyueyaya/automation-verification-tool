# -*- coding: utf-8 -*-
"""env_adapter/env_probe.py — 环境探测（第 2 层）。

调用方禁止自己判断环境；环境问题只允许在本模块与 router 中解决。
复用 scripts/env.py 的窗口/进程/DPI 能力，输出 EnvProfile。
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from contracts import CaptureMethod, EnvProfile, InputMethod  # noqa: E402
import env as env_util  # noqa: E402

REMOTE_SOFTWARE = ("wujie", "sunloginclient", "todesk", "anydesk",
                   "teamviewer", "向日葵", "wujie2")
BROWSER_PROC = {"chrome.exe": "chrome", "msedge.exe": "msedge",
                "360se.exe": "360se", "360chrome.exe": "360chrome",
                "firefox.exe": "firefox"}
ELECTRON_PROC = ("electron", "slack", "discord", "obsidian", "notion",
                 "doubao", "feishu", "lark")


def _integrity_level() -> str:
    """当前进程完整性级别：high / medium / low（UIPI 前置条件）。"""
    try:
        import ctypes
        from ctypes import wintypes
        TOKEN_QUERY = 0x0008
        TokenIntegrityLevel = 25
        h = wintypes.HANDLE()
        if not ctypes.windll.advapi32.OpenProcessToken(
                ctypes.windll.kernel32.GetCurrentProcess(), TOKEN_QUERY,
                ctypes.byref(h)):
            return "medium"
        try:
            buf = ctypes.create_string_buffer(256)
            size = wintypes.DWORD()
            ctypes.windll.advapi32.GetTokenInformation(
                h, TokenIntegrityLevel, buf, 256, ctypes.byref(size))
            # TOKEN_MANDATORY_LABEL: {SID_AND_ATTRIBUTES Label;}
            sid = ctypes.cast(
                ctypes.byref(buf, ctypes.sizeof(wintypes.DWORD)),
                ctypes.POINTER(ctypes.c_void_p)).contents
            # GetSidSubAuthorityCount + GetSidSubAuthority 取最后一位
            count_ptr = ctypes.windll.advapi32.GetSidSubAuthorityCount(sid)
            count = count_ptr.contents.value
            sub = ctypes.windll.advapi32.GetSidSubAuthority(
                sid, count - 1)
            value = sub.contents.value
            if value >= 0x4000:
                return "high"
            if value == 0x2000:
                return "medium"
            return "low"
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return "medium"


def _remote_software() -> str | None:
    try:
        import psutil
        names = set()
        for p in psutil.process_iter(["name"]):
            n = (p.info.get("name") or "").lower()
            if n:
                names.add(n)
        for r in REMOTE_SOFTWARE:
            if any(r in n for n in names):
                return r
    except Exception:
        pass
    return None


def probe_env(window_handle=None) -> EnvProfile:
    """探测目标窗口所属环境，返回 EnvProfile（不缓存，缓存由 env_cache 负责）。"""
    t0 = time.time()
    prof = EnvProfile()
    try:
        prof.dpi_scale = env_util.dpi_for_window(window_handle)[1]
    except Exception:
        pass
    prof.integrity_level = _integrity_level()
    prof.security = _remote_software()

    if window_handle:
        wins = env_util.find_windows(visible_only=True, cache_ttl=0)
        match = next((w for w in wins if w["hwnd"] == window_handle), None)
        if match:
            try:
                import psutil
                proc = psutil.Process(match["pid"])
                pname = (proc.name() or "").lower()
            except Exception:
                pname = ""
            if pname in BROWSER_PROC:
                prof.browser = BROWSER_PROC[pname]
            elif any(k in pname for k in ELECTRON_PROC):
                prof.browser = "electron"
            if prof.security or pname in ("wujie.exe",):
                prof.framework = "wujie"
            elif pname in BROWSER_PROC or prof.browser:
                prof.framework = "native"
    # 焦点可靠性：wujie/远程软件接管时不可靠（无句柄时仅按 security 判断）
    if prof.framework == "wujie" or prof.security:
        prof.focus_reliable = False
    # 默认输入/截图方式由 router 细化；这里给保守默认
    prof.input_method = (InputMethod.HANDLE_POST
                         if not prof.focus_reliable
                         else InputMethod.SEND_INPUT)
    prof.capture_method = CaptureMethod.MSS if not prof.focus_reliable \
        else CaptureMethod.DXCAM
    prof.probe_ms = round((time.time() - t0) * 1000, 2)
    prof.probed_at = time.time()
    return prof
