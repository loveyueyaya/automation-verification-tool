# -*- coding: utf-8 -*-
"""contracts/validators.py — 契约运行时校验。

debug 模式全开；release 模式只校验跨层边界（后续由 config 控制）。
"""
from .enums import SourceEnum
from .stable_id import parse_element_id


def validate_element_id(eid) -> list:
    """返回违规清单（空 = 合法）。"""
    problems = []
    if not eid or not eid.startswith("elem_s:"):
        problems.append("缺 elem_s: 前缀: %r" % eid)
        return problems
    try:
        p = parse_element_id(eid)
    except ValueError as e:
        problems.append(str(e))
        return problems
    if p["handle"] is None and p["control_path"] is None \
            and p["semantic"] is None:
        problems.append("三层全空（至少一层非 none）: %r" % eid)
    return problems


def validate_snapshot(s) -> list:
    problems = []
    if not getattr(s, "trace_id", ""):
        problems.append("trace_id 为空（无 trace 的日志是孤儿）")
    if getattr(s, "window", None) is None:
        problems.append("window 缺失")
    for e in getattr(s, "elements", None) or []:
        problems += ["element %s: %s" % (e.id, p)
                     for p in validate_element_id(e.id)]
    return problems


def validate_resolved_action(a) -> list:
    problems = []
    if not getattr(a, "action", None):
        problems.append("action 为空")
    if not getattr(a, "click_point_phys", None):
        problems.append("click_point_phys 缺失（定位层必须给坐标，LLM 不输出坐标）")
    m = getattr(a, "method", None)
    if m is not None and not isinstance(m, SourceEnum):
        problems.append("method 必须为 SourceEnum（禁止字符串字面量）: %r" % m)
    return problems
