# -*- coding: utf-8 -*-
"""tests/test_select_flow.py — 执行流选择单测（P1 验收）。

覆盖 5 个流（CACHE/NORMAL/LLM/EXCEPTION/HUMAN）的所有分支：
  failure 非空（STRONG>=2 → HUMAN / 其他 → EXCEPTION）
  cache_hit + light_check（exact_repeat → CACHE / 否则 → NORMAL）
  缓存失效后 diff（None 或 significant → LLM / 否则 → NORMAL）
  light_check / exact_repeat 定义验证
"""
import os
import sys
import unittest

# --- contracts 来源引导（P2-2 收尾 #1） ---
_TESTS = os.path.dirname(os.path.abspath(__file__))
_P1 = os.path.dirname(_TESTS)
_IMPL_ROOT = os.path.dirname(_P1)
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _P1)                                 # p1 模式：contracts shim（需先运行 restore_p1_shim.py）
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))  # 默认：契约层唯一实现

from contracts import (Element, Flow, PreviousAction, StateDiff,
                       StateSnapshot, VerificationResult, VerifyLevel,
                       WindowInfo)
from contracts.flow import exact_repeat, light_check, select_flow
from contracts.state_hash import state_hash

EID = "elem_s:a_p:none_h:1"


def state_with(eid=EID, rect=(0, 0, 1000, 1000)):
    return StateSnapshot(
        trace_id="t", timestamp=1.0,
        window=WindowInfo(hwnd=1, title="T", pid=1, rect=rect),
        elements=[Element(id=eid, type="button", text="A",
                          bbox_phys=(100, 100, 200, 130))])


def fail(level, retries):
    return VerificationResult(level=level, status="failed", retries=retries)


class TestSelectFlow(unittest.TestCase):
    # --- failure 非空 ---
    def test_strong_fail_retries_2_human(self):
        self.assertEqual(select_flow(state_with(), False, None,
                                     fail(VerifyLevel.STRONG, 2)), Flow.HUMAN)
        self.assertEqual(select_flow(state_with(), False, None,
                                     fail(VerifyLevel.STRONG, 3)), Flow.HUMAN)

    def test_strong_fail_retries_lt2_exception(self):
        self.assertEqual(select_flow(state_with(), False, None,
                                     fail(VerifyLevel.STRONG, 1)), Flow.EXCEPTION)
        self.assertEqual(select_flow(state_with(), False, None,
                                     fail(VerifyLevel.STRONG, 0)), Flow.EXCEPTION)

    def test_weak_fail_exception(self):
        self.assertEqual(select_flow(state_with(), False, None,
                                     fail(VerifyLevel.WEAK, 5)), Flow.EXCEPTION)

    # --- cache_hit + light_check ---
    def test_cache_hit_exact_repeat_cache(self):
        st = state_with()
        prev = PreviousAction(state_hash=state_hash(st, EID),
                              target_element_id=EID, action="click")
        self.assertEqual(select_flow(st, True, StateDiff(significant=False),
                                     None, prev=prev, target_element_id=EID,
                                     action="click"), Flow.CACHE)

    def test_cache_hit_not_exact_normal(self):
        st = state_with()
        prev = PreviousAction(state_hash="完全不同的hash",
                              target_element_id=EID, action="click")
        self.assertEqual(select_flow(st, True, StateDiff(significant=False),
                                     None, prev=prev, target_element_id=EID,
                                     action="click"), Flow.NORMAL)

    def test_cache_hit_light_ok_no_prev_normal(self):
        self.assertEqual(select_flow(state_with(), True,
                                     StateDiff(significant=False), None,
                                     target_element_id=EID, action="click"),
                         Flow.NORMAL)

    # --- 缓存失效后按 diff 判断 ---
    def test_cache_hit_light_fail_diff_none_llm(self):
        empty = StateSnapshot(trace_id="t",
                              window=WindowInfo(hwnd=1, title="T",
                                                rect=(0, 0, 1000, 1000)),
                              elements=[])
        self.assertEqual(select_flow(empty, True, None, None,
                                     target_element_id=EID), Flow.LLM)

    def test_cache_hit_light_fail_diff_insignificant_normal(self):
        empty = StateSnapshot(trace_id="t",
                              window=WindowInfo(hwnd=1, title="T",
                                                rect=(0, 0, 1000, 1000)),
                              elements=[])
        self.assertEqual(select_flow(empty, True,
                                     StateDiff(significant=False), None,
                                     target_element_id=EID), Flow.NORMAL)

    # --- 无缓存 → diff 判断 ---
    def test_no_cache_diff_none_llm(self):
        self.assertEqual(select_flow(state_with(), False, None, None),
                         Flow.LLM)

    def test_no_cache_diff_significant_llm(self):
        self.assertEqual(select_flow(state_with(), False,
                                     StateDiff(significant=True), None),
                         Flow.LLM)

    def test_no_cache_diff_insignificant_normal(self):
        self.assertEqual(select_flow(state_with(), False,
                                     StateDiff(significant=False), None),
                         Flow.NORMAL)

    # --- light_check / exact_repeat 定义 ---
    def test_light_check(self):
        st = state_with()
        self.assertTrue(light_check(st, EID))
        # 目标元素指纹不在
        empty = StateSnapshot(
            trace_id="t",
            window=WindowInfo(hwnd=1, title="T", rect=(0, 0, 10, 10)),
            elements=[])
        self.assertFalse(light_check(empty, EID))
        # 窗口 rect 变化
        self.assertFalse(light_check(st, EID, baseline_rect=(0, 0, 500, 500)))

    def test_exact_repeat(self):
        st = state_with()
        prev = PreviousAction(state_hash=state_hash(st, EID),
                              target_element_id=EID, action="click")
        self.assertTrue(exact_repeat(st, EID, "click", prev))
        self.assertFalse(exact_repeat(st, EID, "click", None))
        self.assertFalse(exact_repeat(st, EID, "scroll", prev))
        self.assertFalse(exact_repeat(st, None, "click", prev))


if __name__ == "__main__":
    unittest.main()
