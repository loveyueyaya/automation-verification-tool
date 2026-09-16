# -*- coding: utf-8 -*-
"""contracts/errors.py — 契约异常层级与错误码映射。"""
from .enums import ErrorCode


class ContractError(Exception):
    """契约层基类。"""


class EnvUnsupportedError(ContractError):
    code = ErrorCode.ENV_UNSUPPORTED


class ElementNotFoundError(ContractError):
    code = ErrorCode.ELEMENT_NOT_FOUND


class InputFailedError(ContractError):
    code = ErrorCode.INPUT_FAILED


class VerifyFailedError(ContractError):
    code = ErrorCode.VERIFY_FAILED


class NonIdempotentRetryError(ContractError):
    code = ErrorCode.NON_IDEMPOTENT_RETRY


class ContractTimeoutError(ContractError):
    code = ErrorCode.TIMEOUT


class FocusLostError(ContractError):
    code = ErrorCode.FOCUS_LOST


class OccludedError(ContractError):
    code = ErrorCode.OCCLUDED


class CacheMissError(ContractError):
    code = ErrorCode.CACHE_MISS


_ERR_CLASSES = (EnvUnsupportedError, ElementNotFoundError, InputFailedError,
                VerifyFailedError, NonIdempotentRetryError,
                ContractTimeoutError, FocusLostError, OccludedError,
                CacheMissError)


def to_error_code(exc: Exception) -> ErrorCode:
    """异常 → 错误码。未知异常映射为 ENV_UNSUPPORTED（保守降级）。"""
    if isinstance(exc, ContractError):
        return exc.code
    return ErrorCode.ENV_UNSUPPORTED
