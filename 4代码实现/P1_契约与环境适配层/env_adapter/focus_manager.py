# -*- coding: utf-8 -*-
"""env_adapter/focus_manager.py — 前台、置顶、焦点恢复统一入口。

复用 scripts/env.py 的 activate_window；记录原前台，支持恢复。
"""
import ctypes
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import env as env_util  # noqa: E402


class FocusManager:
    def __init__(self):
        self._prev_fg = None

    def ensure_focus(self, window_handle: int) -> bool:
        """激活目标窗口到前台；记录原前台以便 restore。"""
        try:
            self._prev_fg = int(ctypes.windll.user32.GetForegroundWindow())
        except Exception:
            self._prev_fg = None
        return env_util.activate_window(window_handle)

    def restore_focus(self) -> bool:
        """恢复原前台窗口（Chrome 抢前台场景的收尾）。"""
        if self._prev_fg and self._prev_fg:
            return env_util.activate_window(self._prev_fg)
        return True

    def is_foreground(self, window_handle: int) -> bool:
        try:
            return int(ctypes.windll.user32.GetForegroundWindow()) == window_handle
        except Exception:
            return False
