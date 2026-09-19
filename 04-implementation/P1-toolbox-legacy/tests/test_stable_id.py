# -*- coding: utf-8 -*-
"""tests/test_stable_id.py — 元素指纹单测（P1 验收）。

覆盖：三层生成 / 空段 none / 用途区分（定位 vs 缓存）/
      碰撞消歧 / 逐层回退 / 非法格式。
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

from contracts.stable_id import (element_id, parse_element_id,
                                 resolve_for_action, resolve_for_cache)


class TestStableId(unittest.TestCase):
    def test_three_layer_generation(self):
        eid = element_id(semantic_hash="a3f2",
                         control_path="Window/Edit[1]", handle=0x1A2B)
        # 用户规格：handle 段带 0x 前缀（elem_s:none_p:none_h:0x1A2B）
        self.assertEqual(eid, "elem_s:a3f2_p:Window/Edit[1]_h:0x1a2b")
        p = parse_element_id(eid)
        self.assertEqual(p["semantic_hash"], "a3f2")
        self.assertEqual(p["control_path"], "Window/Edit[1]")
        self.assertEqual(p["handle"], 0x1A2B)

    def test_empty_segments_use_none(self):
        eid = element_id(handle=0x1A2B)
        self.assertEqual(eid, "elem_s:none_p:none_h:0x1a2b")
        p = parse_element_id(eid)
        self.assertIsNone(p["semantic"])
        self.assertIsNone(p["control_path"])
        self.assertEqual(p["handle"], 0x1A2B)

    def test_action_resolution_prefers_handle(self):
        eid = element_id("a3f2", "Window/Edit[1]", 0x1A2B)
        r = resolve_for_action(eid)
        self.assertEqual([layer for layer, _ in r],
                         ["handle", "control_path", "semantic"])
        self.assertEqual(r[0], ("handle", 0x1A2B))

    def test_cache_resolution_prefers_semantic(self):
        eid = element_id("a3f2", "Window/Edit[1]", 0x1A2B)
        r = resolve_for_cache(eid)
        self.assertEqual([layer for layer, _ in r],
                         ["semantic", "control_path", "handle"])
        self.assertEqual(r[0], ("semantic", "a3f2"))

    def test_collision_disambiguation(self):
        a = element_id("a3f2", disambiguator="login")
        b = element_id("a3f2", disambiguator="register")
        self.assertNotEqual(a, b)
        self.assertEqual(parse_element_id(a)["disambiguator"], "login")
        self.assertEqual(parse_element_id(b)["disambiguator"], "register")

    def test_layer_fallback(self):
        # 只有 handle
        self.assertEqual(resolve_for_action(element_id(handle=0x1A2B)),
                         [("handle", 0x1A2B)])
        # handle + path，缺 semantic
        r = resolve_for_action(element_id(control_path="P", handle=0x1A2B))
        self.assertEqual([l for l, _ in r], ["handle", "control_path"])
        # 全空 → 无可用层
        self.assertEqual(resolve_for_action("elem_s:none_p:none_h:none"), [])
        # semantic 失效（none）后 handle 仍可用，不拉垮其他层
        r = resolve_for_action("elem_s:none_p:Window/Edit[1]_h:1a2b")
        self.assertEqual(r, [("handle", 0x1A2B),
                             ("control_path", "Window/Edit[1]")])

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_element_id("bad_id")
        with self.assertRaises(ValueError):
            parse_element_id("elem_s:a3f2")          # 缺 _p:/_h: 段
        with self.assertRaises(ValueError):
            parse_element_id("elem_s:none_p:none_h:zz")  # 非法 handle


if __name__ == "__main__":
    unittest.main()
