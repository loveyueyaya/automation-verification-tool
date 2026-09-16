# -*- coding: utf-8 -*-
"""env_adapter/input_router.py — 输入注入路由（声明式规则表）。

按 EnvProfile 决定输入方式：SendInput / 句柄直投 / WM_CHAR / 驱动级。
新增环境 = 加一行规则，禁止在调用方打补丁。
"""
from contracts import ActionType, EnvProfile, InputMethod

_INPUT_RULES = [
    # (判定, 方式, 原因)
    (lambda e: e.framework == "wujie", InputMethod.HANDLE_POST,
     "wujie 拦截 SendInput 鼠标"),
    (lambda e: e.integrity_level == "low", InputMethod.HANDLE_POST,
     "低完整性 UIPI 静默拦截"),
    (lambda e: not e.focus_reliable, InputMethod.HANDLE_POST,
     "焦点不可靠（远程软件接管）"),
    (lambda e: e.security is not None, InputMethod.HANDLE_POST,
     "安全软件可能拦截全局输入"),
]


def route_input(env: EnvProfile, action_type: ActionType | None = None) -> InputMethod:
    """路由输入注入方式。文本输入在可靠环境优先 SendInput。"""
    for cond, method, _why in _INPUT_RULES:
        if cond(env):
            return method
    if action_type == ActionType.TYPE:
        return InputMethod.SEND_INPUT
    return InputMethod.SEND_INPUT


def route_reason(env: EnvProfile) -> str:
    """返回命中的规则原因（审计用）。无命中返回默认。"""
    for cond, _method, why in _INPUT_RULES:
        if cond(env):
            return why
    return "默认 SendInput"
