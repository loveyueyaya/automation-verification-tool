# -*- coding: utf-8 -*-
"""tests/test_trace_span.py — 跨进程 trace 字段单测（P2-3 Step1）。

覆盖三条：
  1. 新字段默认值 —— 不传 span_id/parent_span 时为空串（向后兼容）
  2. 旧构造方式 —— 位置参数 6 个（trace_id/layer/step/ts_start/ts_end/meta）仍可构造，duration_ms 不变
  3. 三元组赋值 —— span_id/parent_span 可写、可 JSON 序列化、字段顺序在末尾
"""
import json
import os
import sys
import unittest
from dataclasses import fields

_TESTS = os.path.dirname(os.path.abspath(__file__))
_P1 = os.path.dirname(_TESTS)
_IMPL_ROOT = os.path.dirname(_P1)
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _P1)
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))

from contracts.models import TraceSpan


class TestTraceSpanSpanFields(unittest.TestCase):
    def test_default_empty(self):
        """不传新字段时默认为空串（旧调用方零改动）。"""
        s = TraceSpan("t1", "perception", "see", 0.0, 0.5)
        self.assertEqual(s.span_id, "")
        self.assertEqual(s.parent_span, "")

    def test_legacy_positional_construction(self):
        """旧写法（6 个位置参数）仍然成立，且 duration_ms 语义不变。"""
        s = TraceSpan("t1", "perception", "see", 1.0, 1.5, {"k": 1})
        self.assertEqual((s.trace_id, s.layer, s.step, s.meta),
                         ("t1", "perception", "see", {"k": 1}))
        self.assertEqual(s.duration_ms, 500.0)
        self.assertEqual(s.span_id, "")
        self.assertEqual(s.parent_span, "")

    def test_span_triple_and_serializable(self):
        """三元组可赋值、可序列化，且新字段位于字段列表末尾（位置参数兼容的前提）。"""
        s = TraceSpan("t1", "execution", "click", 2.0, 2.25, {}, "t1-s1", "t1-s0")
        self.assertEqual((s.span_id, s.parent_span), ("t1-s1", "t1-s0"))
        d = json.loads(json.dumps(s.__dict__))
        self.assertEqual(d["span_id"], "t1-s1")
        self.assertEqual(d["parent_span"], "t1-s0")
        self.assertEqual([f.name for f in fields(TraceSpan)][-2:],
                         ["span_id", "parent_span"])


if __name__ == "__main__":
    unittest.main()
