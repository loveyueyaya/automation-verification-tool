# -*- coding: utf-8 -*-
"""contracts/enums.py — 契约枚举（P1）。

硬规则：所有脚本禁止用字符串字面量代替以下枚举（"ocr"/"uia"/"handle" 等视为违规）。
"""
from enum import Enum


class SourceEnum(str, Enum):
    """坐标/目标来源。定位优先级：HANDLE > UIA > CACHE > OCR；
    OCR 只做校验，不做坐标来源。MANUAL 仅 --force-xy 显式声明时使用。"""
    HANDLE = "handle"
    UIA = "uia"
    OCR = "ocr"
    CACHE = "cache"
    TEMPLATE = "template"
    MANUAL = "manual"
    RULE = "rule"
    DIAGNOSE = "diagnose"


class CoordType(str, Enum):
    PHYS = "phys"
    LOGIC = "logic"


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    DRAG = "drag"
    SCROLL = "scroll"
    WAIT = "wait"
    ASSERT = "assert"


class InputMethod(str, Enum):
    """输入注入方式，由 env_adapter.input_router 按 EnvProfile 路由。"""
    SEND_INPUT = "send_input"
    HANDLE_POST = "handle_post"
    WM_CHAR = "wm_char"
    DRIVER = "driver"


class CaptureMethod(str, Enum):
    """截图方式，由 env_adapter.capture_router 按 EnvProfile 路由。"""
    DXCAM = "dxcam"
    MSS = "mss"
    BITBLT = "bitblt"
    PRINT_WINDOW = "print_window"


class VerifyLevel(str, Enum):
    STRONG = "strong"
    WEAK = "weak"
    NONE = "none"


class Flow(str, Enum):
    """执行流（用户评分规格，5 个）：CACHE / NORMAL / LLM / EXCEPTION / HUMAN。"""
    CACHE = "cache"
    NORMAL = "normal"
    LLM = "llm"
    EXCEPTION = "exception"
    HUMAN = "human"


class ErrorCode(str, Enum):
    ENV_UNSUPPORTED = "env_unsupported"
    ELEMENT_NOT_FOUND = "element_not_found"
    INPUT_FAILED = "input_failed"
    VERIFY_FAILED = "verify_failed"
    NON_IDEMPOTENT_RETRY = "non_idempotent_retry"
    TIMEOUT = "timeout"
    FOCUS_LOST = "focus_lost"
    OCCLUDED = "occluded"
    CACHE_MISS = "cache_miss"
