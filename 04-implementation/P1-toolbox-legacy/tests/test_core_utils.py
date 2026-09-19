# -*- coding: utf-8 -*-
"""tests/test_core_utils.py — core/utils 公共工具单测（P2-3 Step2 单源化）。

覆盖：jdefault（合并 locate/uitool 两份漂移实现）、键名↔VK 映射、
     进程查询、远控名单常量、JSON 读写。
进程类用例用当前进程自身（肯定存在），不依赖外部程序。
"""
import json
import os
import sys
import tempfile
import unittest
from enum import Enum

_TESTS = os.path.dirname(os.path.abspath(__file__))
_P1 = os.path.dirname(_TESTS)
_IMPL_ROOT = os.path.dirname(_P1)
sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))   # core 包（与 contracts 来源无关）

from core.constants import REMOTE_SOFTWARE
from core.utils import (KEY_MAP, jdefault, jdumps, key_name, vk_of,
                        pids_by_name, proc_running, find_pid_by_name,
                        proc_stats, load_json, save_json)


class Color(Enum):
    RED = "r"


class TestJsonDefault(unittest.TestCase):
    def test_enum_to_value(self):
        self.assertEqual(jdefault(Color.RED), "r")

    def test_unknown_to_str(self):
        self.assertEqual(jdefault(123), "123")

    def test_jdumps_no_ascii(self):
        self.assertEqual(jdumps({"c": Color.RED}), '{"c": "r"}')


class TestKeyMap(unittest.TestCase):
    def test_name_to_vk(self):
        self.assertEqual(vk_of("F10"), 0x79)
        self.assertEqual(vk_of("insert"), 0x2D)
        self.assertEqual(vk_of("A"), 65)

    def test_vk_number_and_hex(self):
        self.assertEqual(vk_of("0x79"), 0x79)
        self.assertEqual(vk_of("121"), 121)

    def test_roundtrip_and_unknown(self):
        self.assertEqual(key_name(vk_of("F10")), "F10")
        self.assertIsNone(vk_of("NO_SUCH_KEY"))
        self.assertEqual(key_name(0x9999), "VK39321")
        self.assertIn("F1", KEY_MAP)


class TestProc(unittest.TestCase):
    def test_self_process_found(self):
        """用当前进程自身验证：三种查法都能命中同一个 python 进程名。"""
        name = os.path.basename(sys.executable)          # python.exe
        self.assertTrue(pids_by_name(name), "应能查到自身进程")
        self.assertIsNotNone(proc_running(name))
        self.assertIsNotNone(find_pid_by_name(name))

    def test_missing_process_returns_empty(self):
        self.assertEqual(pids_by_name("definitely_not_a_real_process.exe"), [])
        self.assertIsNone(proc_running("definitely_not_a_real_process.exe"))

    def test_proc_stats_self(self):
        st = proc_stats(os.getpid())
        self.assertIsNotNone(st)
        self.assertEqual(st["pid"], os.getpid())
        self.assertGreaterEqual(st["cpu_ms"], 0)
        self.assertGreater(st["mem_mb"], 0)


class TestRemoteSoftwareConstant(unittest.TestCase):
    def test_merged_list(self):
        """两份旧名单的并集：testbar 8 项 ∪ env_probe 7 项 = 11 项。"""
        self.assertEqual(len(REMOTE_SOFTWARE), 11)
        for n in ("wujie", "sunloginclient", "todesk", "anydesk",
                  "teamviewer", "rper", "uu", "mstsc", "qclient"):
            self.assertIn(n, REMOTE_SOFTWARE)


class TestJsonFile(unittest.TestCase):
    def test_save_and_load(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "sub", "cfg.json")
        self.assertTrue(save_json(p, {"a": 1, "c": Color.RED}))
        self.assertEqual(load_json(p), {"a": 1, "c": "r"})
        self.assertIsNone(load_json(os.path.join(d, "missing.json")))


if __name__ == "__main__":
    unittest.main()
