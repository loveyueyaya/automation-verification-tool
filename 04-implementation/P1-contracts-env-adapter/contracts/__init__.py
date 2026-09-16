# -*- coding: utf-8 -*-
"""contracts — 契约层（横切 A）。

所有脚本 import contracts，禁止自定义同义结构、禁止字符串字面量代替枚举。

用法：
  from contracts import SourceEnum, ActionType, StateSnapshot, select_flow, ...
"""
from .enums import (ActionType, CaptureMethod, CoordType, ErrorCode, Flow,
                    InputMethod, SourceEnum, VerifyLevel)
from .errors import (CacheMissError, ContractError, ContractTimeoutError,
                     ElementNotFoundError, EnvUnsupportedError, FocusLostError,
                     InputFailedError, NonIdempotentRetryError,
                     OccludedError, VerifyFailedError, to_error_code)
from .models import (ActionIntent, Element, EnvProfile, ExecutionResult,
                     FallbackAction, OcrItem, ResolvedAction,
                     ResourceSnapshot, Rule, StateDiff, StateSnapshot,
                     TraceSpan, VerificationResult, WindowInfo)
from .version import CONTRACT_VERSION, check_contract_version
from .stable_id import (element_id, parse_element_id, resolve_for_action,
                        resolve_for_cache)
from .state_hash import normalize_text, select_key_elements, state_hash
from .flow import (PreviousAction, exact_repeat, light_check, select_flow)
from .validators import (validate_element_id, validate_resolved_action,
                         validate_snapshot)

__all__ = [
    # enums
    "SourceEnum", "CoordType", "ActionType", "InputMethod", "CaptureMethod",
    "VerifyLevel", "Flow", "ErrorCode",
    # errors
    "ContractError", "EnvUnsupportedError", "ElementNotFoundError",
    "InputFailedError", "VerifyFailedError", "NonIdempotentRetryError",
    "ContractTimeoutError", "FocusLostError", "OccludedError", "CacheMissError",
    "to_error_code",
    # models
    "TraceSpan", "WindowInfo", "EnvProfile", "Element", "OcrItem",
    "StateSnapshot", "ActionIntent", "ResolvedAction", "ExecutionResult",
    "VerificationResult", "StateDiff", "Rule", "ResourceSnapshot",
    "FallbackAction",
    # version
    "CONTRACT_VERSION", "check_contract_version",
    # stable_id
    "element_id", "parse_element_id", "resolve_for_action", "resolve_for_cache",
    # state_hash
    "normalize_text", "select_key_elements", "state_hash",
    # flow
    "PreviousAction", "exact_repeat", "light_check", "select_flow",
    # validators
    "validate_element_id", "validate_resolved_action", "validate_snapshot",
]
