# -*- coding: utf-8 -*-
"""env_adapter — 运行时环境适配层（第 2 层，新增核心）。

调用方禁止自己判断环境；环境问题只允许在本包解决。
"""
from .env_cache import EnvCache
from .env_probe import probe_env
from .input_router import route_input, route_reason
from .capture_router import route_capture, capture_reason
from .focus_manager import FocusManager
from .fallback_policy import FALLBACK_TABLE, resolve

__all__ = ["EnvCache", "probe_env", "route_input", "route_reason",
           "route_capture", "capture_reason", "FocusManager",
           "FALLBACK_TABLE", "resolve"]
