# -*- coding: utf-8 -*-
"""contracts/version.py — 契约版本与一致性校验。"""
CONTRACT_VERSION = "2026.09.16-P1"


def check_contract_version(module) -> bool:
    """校验模块导出的 CONTRACT_VERSION 与当前一致。启动时全模块校验。"""
    return getattr(module, "CONTRACT_VERSION", None) == CONTRACT_VERSION
