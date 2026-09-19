# -*- coding: utf-8 -*-
"""tests/test_state_hash.py — 状态哈希单测（P1 验收）。

覆盖：参与/不参与字段、2% 位置容差、编辑框变化 → hash 变、
      target_hint 圈定、文本规范化（全角→半角）。
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

from contracts import Element, OcrItem, StateSnapshot, WindowInfo
from contracts.state_hash import normalize_text, state_hash


def btn(eid, text, x=100, y=100, w=100, h=30, etype="button"):
    return Element(id=eid, type=etype, text=text,
                   bbox_phys=(x, y, x + w, y + h))


def make_snapshot(elems, title="Test", rect=(0, 0, 1000, 1000)):
    return StateSnapshot(
        trace_id="t1", timestamp=1.0,
        window=WindowInfo(hwnd=1, title=title, pid=1, rect=rect),
        elements=elems,
        ocr=[OcrItem(text="任意内容", bbox_phys=(0, 0, 10, 10),
                     confidence=0.9)])


class TestStateHash(unittest.TestCase):
    def test_ocr_not_participating(self):
        s1 = make_snapshot([btn("e1", "登录", 100, 100)])
        s2 = make_snapshot([btn("e1", "登录", 100, 100)])
        s2.ocr[0].text = "完全不同的OCR内容"
        self.assertEqual(state_hash(s1), state_hash(s2))

    def test_button_text_change_changes_hash(self):
        s1 = make_snapshot([btn("e1", "登录", 100, 100)])
        s2 = make_snapshot([btn("e1", "退出", 100, 100)])
        self.assertNotEqual(state_hash(s1), state_hash(s2))

    def test_2pct_grid_tolerance(self):
        # 窗口 1000 → 2% = 20px；100→110 同格（hash 不变）；100→130 跨格（变）
        s1 = make_snapshot([btn("e1", "登录", 100, 100)])
        s2 = make_snapshot([btn("e1", "登录", 110, 100)])
        self.assertEqual(state_hash(s1), state_hash(s2))
        s3 = make_snapshot([btn("e1", "登录", 130, 100)])
        self.assertNotEqual(state_hash(s1), state_hash(s3))

    def test_input_text_change_changes_hash(self):
        s1 = make_snapshot([btn("e1", "abc", 200, 200, 200, 30, "input")])
        s2 = make_snapshot([btn("e1", "abcd", 200, 200, 200, 30, "input")])
        self.assertNotEqual(state_hash(s1), state_hash(s2))

    def test_target_hint_scopes(self):
        a = "elem_s:a_p:none_h:1"
        b = "elem_s:b_p:none_h:2"
        s1 = make_snapshot([btn(a, "A", 100, 100), btn(b, "B", 300, 300)])
        s2 = make_snapshot([btn(a, "A", 100, 100), btn(b, "B改", 300, 300)])
        # 改非目标、非输入框的元素 → hash 不变（target_hint 圈定生效）
        self.assertEqual(state_hash(s1, a), state_hash(s2, a))
        # 改目标自身 → 变
        s3 = make_snapshot([btn(a, "A改", 100, 100), btn(b, "B", 300, 300)])
        self.assertNotEqual(state_hash(s1, a), state_hash(s3, a))

    def test_text_normalization(self):
        s1 = make_snapshot([btn("e1", "ＡＢＣ", 100, 100)])   # 全角
        s2 = make_snapshot([btn("e1", "abc", 100, 100)])
        self.assertEqual(state_hash(s1), state_hash(s2))

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  ＡＢＣ  "), "abc")
        self.assertEqual(normalize_text("Hello  World"), "hello world")


if __name__ == "__main__":
    unittest.main()
