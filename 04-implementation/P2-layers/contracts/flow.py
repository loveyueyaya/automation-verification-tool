# -*- coding: utf-8 -*-
"""contracts/flow.py — 执行流选择（纯函数；P2 迁往 orchestrator/flow.py）。

Flow 5 个：CACHE / NORMAL / LLM / EXCEPTION / HUMAN。
规则（用户评分规格，按序短路）：
  1. failure 非空：
       STRONG 失败且 retries >= 2 → HUMAN
       其他 failure → EXCEPTION
  2. cache_hit 且 light_check 通过：
       exact_repeat（历史动作完全一致）→ CACHE
       否则 → NORMAL
  3. diff 为空或 significant → LLM
  4. 其他 → NORMAL
"""
from dataclasses import dataclass

from .enums import Flow, VerifyLevel
from .state_hash import state_hash


@dataclass
class PreviousAction:
    """上一次动作（exact_repeat 判定依据）。"""
    state_hash: str = ""
    target_element_id: str = ""
    action: str = ""


def light_check(state, target_element_id=None, baseline_rect=None) -> bool:
    """轻量校验：目标元素指纹仍在 + 窗口 rect 未变。"""
    if target_element_id:
        elems = getattr(state, "elements", None) or []
        if not any(getattr(e, "id", "") == target_element_id for e in elems):
            return False
    win = getattr(state, "window", None)
    if baseline_rect is not None and win is not None:
        if tuple(win.rect) != tuple(baseline_rect):
            return False
    return True


def exact_repeat(state, target_element_id, action, prev) -> bool:
    """历史动作完全一致：同 state_hash + 同 target_element_id + 同 action。"""
    if prev is None:
        return False
    cur = state_hash(state, target_element_id or None)
    return (prev.state_hash == cur
            and (prev.target_element_id or None) == (target_element_id or None)
            and prev.action == action)


def select_flow(state, cache_hit, diff, failure, *, prev=None,
                target_element_id=None, action=None, baseline_rect=None) -> Flow:
    """选择执行流。纯函数，无 IO。"""
    if failure is not None:
        if (getattr(failure, "level", None) == VerifyLevel.STRONG
                and (getattr(failure, "retries", 0) or 0) >= 2):
            return Flow.HUMAN
        return Flow.EXCEPTION
    if cache_hit and light_check(state, target_element_id, baseline_rect):
        if exact_repeat(state, target_element_id, action, prev):
            return Flow.CACHE
        return Flow.NORMAL
    if diff is None or getattr(diff, "significant", False):
        return Flow.LLM
    return Flow.NORMAL
