# -*- coding: utf-8 -*-
"""env_adapter/capture_router.py — 截图方式路由（声明式规则表）。

按 EnvProfile 决定截图方式：dxcam / mss / bitblt / print_window。
"""
from contracts import CaptureMethod, EnvProfile

_CAPTURE_RULES = [
    (lambda e: e.framework == "wujie" or not e.focus_reliable,
     CaptureMethod.MSS, "远程/遮挡环境 dxcam 易瞬断"),
    (lambda e: e.security is not None, CaptureMethod.MSS,
     "安全软件环境用 mss 兜底"),
]


def route_capture(env: EnvProfile) -> CaptureMethod:
    for cond, method, _why in _CAPTURE_RULES:
        if cond(env):
            return method
    return CaptureMethod.DXCAM


def capture_reason(env: EnvProfile) -> str:
    for cond, _method, why in _CAPTURE_RULES:
        if cond(env):
            return why
    return "默认 dxcam"
