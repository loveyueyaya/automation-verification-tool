# -*- coding: utf-8 -*-
"""重建等价性最小测试：覆盖两处"实现差异"的核心行为。

1. uitool.verify_text —— 重建引入中间变量 cmd / items falsy 保护
   核心行为：构造 OCR 子进程命令列表 → 调 _sub → 解析 hits → 返回
   {found, items} 并写入时间线审计字段 (src/conf/chain/result)。
2. env.find_windows —— 缓存初始化形态（重建 None+判空 vs 原始 dict+下标）
   核心行为：首次调用枚举、cache_ttl 内命中缓存不重枚举、
   过期重枚举、cache_ttl<=0 不读不写缓存。
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# --- contracts 来源引导（P2-2 收尾 #1） ---
_TESTS = os.path.dirname(os.path.abspath(__file__))
_P1 = os.path.dirname(_TESTS)
sys.path.insert(0, os.path.join(_P1, "scripts"))            # env/uitool 等
_IMPL_ROOT = os.path.dirname(_P1)
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _P1)                                 # p1 模式：contracts shim（需先运行 restore_p1_shim.py）
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))  # 默认：契约层唯一实现

import env
import uitool


class TestVerifyTextEquiv(unittest.TestCase):
    """覆盖 verify_text 核心行为（原始/重建共享的契约）。"""

    def _session(self):
        d = tempfile.mkdtemp(prefix="vt_equiv_")
        os.makedirs(os.path.join(d, "shots"), exist_ok=True)
        return d

    def test_verify_text_command_list_full(self):
        """text+region 都存在时，_sub 收到的命令列表必须含 --filter 与 --region。"""
        session = self._session()
        with mock.patch.object(uitool.shot_mod, "get_engine") as mg, \
                mock.patch.object(uitool, "_sub",
                                  return_value={"items": []}) as sub:
            eng = mock.MagicMock()
            import numpy as np
            eng.grab.return_value = np.zeros((16, 16, 3), dtype=np.uint8)
            mg.return_value = eng
            uitool.verify_text(session, "确定", region="0,0,100,100")
        args = sub.call_args[0][0]
        shot_path = os.path.join(session, "shots", "verify.png")
        self.assertEqual(
            args,
            ["ocr.py", "--image", shot_path,
             "--filter", "确定", "--region", "0,0,100,100"])
        self.assertTrue(os.path.exists(shot_path), "截图证据必须落盘")

    def test_verify_text_command_list_no_filter(self):
        """text=None 时命令列表不得含 --filter。"""
        session = self._session()
        with mock.patch.object(uitool.shot_mod, "get_engine") as mg, \
                mock.patch.object(uitool, "_sub",
                                  return_value={"items": []}) as sub:
            eng = mock.MagicMock()
            import numpy as np
            eng.grab.return_value = np.zeros((16, 16, 3), dtype=np.uint8)
            mg.return_value = eng
            uitool.verify_text(session, None)
        args = sub.call_args[0][0]
        shot_path = os.path.join(session, "shots", "verify.png")
        self.assertEqual(args, ["ocr.py", "--image", shot_path])

    def test_verify_text_return_and_timeline_audit(self):
        """命中时返回 {found:True, items} 且时间线记录 src/conf/chain/result。"""
        session = self._session()
        fake_items = [{"text": "确定", "confidence": 0.93,
                       "box": [[0, 0], [10, 0], [10, 10], [0, 10]]}]
        with mock.patch.object(uitool.shot_mod, "get_engine") as mg, \
                mock.patch.object(uitool, "_sub",
                                  return_value={"items": fake_items}) as sub:
            eng = mock.MagicMock()
            import numpy as np
            eng.grab.return_value = np.zeros((16, 16, 3), dtype=np.uint8)
            mg.return_value = eng
            r = uitool.verify_text(session, "确定")
        self.assertTrue(r["found"])
        self.assertEqual(r["items"], fake_items)
        log_path = os.path.join(session, "timeline.jsonl")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f.read().splitlines() if x.strip()]
        last = rows[-1]
        self.assertEqual(last["phase"], "verify")
        self.assertEqual(last["action"], "ocr_result")
        self.assertEqual(last["result"], "ok")
        self.assertEqual(last["src"], "ocr")
        self.assertEqual(last["conf"], 0.93)
        self.assertEqual(last["chain"], ["ocr"])
        self.assertEqual(last["target"], "确定")
        self.assertEqual(last["note"], "命中 1 处")

    def test_verify_text_miss_result_fail(self):
        """未命中时返回 found:False 且时间线 result=fail。"""
        session = self._session()
        with mock.patch.object(uitool.shot_mod, "get_engine") as mg, \
                mock.patch.object(uitool, "_sub", return_value={}) as sub:
            eng = mock.MagicMock()
            import numpy as np
            eng.grab.return_value = np.zeros((16, 16, 3), dtype=np.uint8)
            mg.return_value = eng
            r = uitool.verify_text(session, "不存在")
        self.assertFalse(r["found"])
        self.assertEqual(r["items"], [])
        with open(os.path.join(session, "timeline.jsonl"),
                  encoding="utf-8") as f:
            rows = [json.loads(x)
                    for x in f.read().splitlines() if x.strip()]
        self.assertEqual(rows[-1]["result"], "fail")
        self.assertEqual(rows[-1]["src"], "ocr")


class TestFindWindowsCacheEquiv(unittest.TestCase):
    """覆盖 find_windows 缓存核心行为（原始 dict+下标 vs 重建 None+判空）。"""

    def setUp(self):
        env._find_windows_cache = None  # 与重建版模块级初始形态一致
        self.calls = {"n": 0}
        self.hwnd = env.ctypes.windll.user32.GetDesktopWindow()

    def _fake_enum(self, proc, lparam):
        self.calls["n"] += 1
        proc(self.hwnd, 0)
        return True

    def test_first_call_enumerates_and_caches(self):
        """首次调用必须枚举，且 cache_ttl>0 时写入缓存。"""
        with mock.patch.object(env.ctypes.windll.user32, "EnumWindows",
                               side_effect=self._fake_enum):
            r1 = env.find_windows(cache_ttl=10)
        self.assertEqual(self.calls["n"], 1)
        self.assertEqual(len(r1), 1)
        self.assertIn("pid", r1[0], "返回必须含 pid 字段")
        self.assertIsNotNone(env._find_windows_cache)
        self.assertEqual(env._find_windows_cache["args"],
                         (None, None, True, None))

    def test_cache_hit_within_ttl_no_re_enum(self):
        """cache_ttl 内第二次调用必须命中缓存，不再枚举。"""
        with mock.patch.object(env.ctypes.windll.user32, "EnumWindows",
                               side_effect=self._fake_enum):
            r1 = env.find_windows(cache_ttl=10)
            r2 = env.find_windows(cache_ttl=10)
        self.assertEqual(self.calls["n"], 1, "缓存命中，不得重枚举")
        self.assertEqual(r1, r2, "两次结果必须完全一致")

    def test_cache_expired_re_enumerates(self):
        """缓存过期后必须重新枚举。用 mock time 推进 5s（ttl=3）。"""
        with mock.patch.object(env.ctypes.windll.user32, "EnumWindows",
                               side_effect=self._fake_enum), \
                mock.patch.object(env.time, "time",
                                  side_effect=[100.0, 100.0,
                                               105.0, 105.0]):
            r1 = env.find_windows(cache_ttl=3)
            r2 = env.find_windows(cache_ttl=3)
        self.assertEqual(self.calls["n"], 2, "过期后必须重枚举")

    def test_ttl_zero_no_cache_read_or_write(self):
        """cache_ttl=0 不读缓存（每次都枚举）也不写缓存。"""
        with mock.patch.object(env.ctypes.windll.user32, "EnumWindows",
                               side_effect=self._fake_enum):
            env.find_windows(cache_ttl=0)
            env.find_windows(cache_ttl=0)
        self.assertEqual(self.calls["n"], 2, "ttl=0 每次都要枚举")

    def test_ttl_zero_does_not_overwrite_cache(self):
        """cache_ttl=0 不得把 _find_windows_cache 置为非空。"""
        with mock.patch.object(env.ctypes.windll.user32, "EnumWindows",
                               side_effect=self._fake_enum):
            env.find_windows(cache_ttl=0)
        self.assertIsNone(env._find_windows_cache,
                          "ttl=0 不得写缓存")


class TestLocByTemplateEquiv(unittest.TestCase):
    """locate.loc_by_template：模板匹配 + 阈值判断 + 返回结构。"""

    def _patch_cv(self, max_val=0.95, match_loc=(5, 6), tpl_ok=True,
                  img_ok=True):
        import numpy as np
        fake = unittest.mock.MagicMock()
        fake.TM_CCOEFF_NORMED = 5
        fake.imread.side_effect = lambda p, f=None: (
            np.zeros((10, 10, 3), dtype=np.uint8) if img_ok else None)
        fake.matchTemplate.return_value = np.zeros((1, 1), dtype=np.float32)
        fake.minMaxLoc.return_value = (0.0, max_val, (0, 0), match_loc)
        return unittest.mock.patch.dict(sys.modules, {"cv2": fake})

    def test_hit_returns_standard_shape(self):
        import locate
        with unittest.mock.patch.object(
                locate.cache_mod, "config",
                return_value={"sim_threshold": 0.8}), \
                self._patch_cv():
            r = locate.loc_by_template("t.png", "i.png")
        self.assertEqual(len(r), 1)
        it = r[0]
        self.assertEqual(it["x"], 5)
        self.assertEqual(it["y"], 6)
        self.assertEqual(it["w"], 10)
        self.assertEqual(it["h"], 10)
        self.assertEqual(it["cx"], 10)
        self.assertEqual(it["cy"], 11)
        self.assertEqual(it["source"], "template")
        self.assertEqual(it["confidence"], 0.95)

    def test_below_threshold_returns_empty(self):
        import locate
        with unittest.mock.patch.object(
                locate.cache_mod, "config",
                return_value={"sim_threshold": 0.8}), \
                self._patch_cv(max_val=0.3):
            r = locate.loc_by_template("t.png", "i.png")
        self.assertEqual(r, [])

    def test_unreadable_image_returns_empty(self):
        import locate
        with unittest.mock.patch.object(
                locate.cache_mod, "config",
                return_value={"sim_threshold": 0.8}), \
                self._patch_cv(img_ok=False):
            r = locate.loc_by_template("t.png", "i.png")
        self.assertEqual(r, [])


class TestTimelineShotEquiv(unittest.TestCase):
    """timeline.Timeline.shot：截图落盘 + 相对路径返回。"""

    def test_shot_saves_png_relative_path(self):
        import numpy as np
        import timeline as timeline_mod
        d = tempfile.mkdtemp(prefix="tl_shot_")
        fake_shot = unittest.mock.MagicMock()
        fake_shot.get_engine.return_value.grab.return_value = \
            np.zeros((8, 8, 3), dtype=np.uint8)
        with unittest.mock.patch.dict(sys.modules, {"shot": fake_shot}):
            t = timeline_mod.Timeline(d)
            rel = t.shot(label="final")
        self.assertTrue(rel.startswith("shots" + os.sep), rel)
        full = os.path.join(d, rel)
        self.assertTrue(os.path.exists(full))
        self.assertTrue(full.endswith(".png"))


class TestTimelineReportEquiv(unittest.TestCase):
    """timeline.report：延迟统计 + >2s 异常标注 + HTML 生成 + 空时间线。"""

    def _mk_session(self, rows):
        d = tempfile.mkdtemp(prefix="tl_report_")
        with open(os.path.join(d, "timeline.jsonl"), "w",
                  encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return d

    def test_report_md_stats_and_slow_flag(self):
        import timeline as timeline_mod
        rows = [
            {"ts": "t1", "step": 1, "phase": "click", "action": "click",
             "target": "A", "method": "sendinput", "result": "ok",
             "latency_ms": 100, "src": "handle", "conf": 1.0, "chain": [],
             "evidence": ""},
            {"ts": "t2", "step": 2, "phase": "click", "action": "click",
             "target": "B", "method": "sendinput", "result": "ok",
             "latency_ms": 300, "src": "handle", "conf": 1.0, "chain": []},
            {"ts": "t3", "step": 3, "phase": "verify", "action": "ocr",
             "target": "C", "method": "paddle", "result": "ok",
             "latency_ms": 2500, "src": "ocr", "conf": 0.9,
             "chain": ["ocr"]},
        ]
        d = self._mk_session(rows)
        html = os.path.join(d, "report.html")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            timeline_mod.report(d, html)
        md_path = os.path.join(d, "report.md")
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        # 分阶段统计：click 两行 100/300 → mean 200.0、P50=100、P95=300、max=300
        self.assertIn("## 分阶段延迟统计（ms）", md)
        self.assertIn("| click | 2 | 200.0 | 100.0 | 300.0 | 300 |", md)
        # >2000 异常标注
        self.assertIn("## 延迟异常（>2s，卡顿/卡点自暴露）", md)
        self.assertIn("2500", md)
        # HTML
        self.assertTrue(os.path.exists(html))
        with open(html, encoding="utf-8") as f:
            html_txt = f.read()
        self.assertIn("<table>", html_txt)
        self.assertIn("2500", html_txt)

    def test_report_empty_timeline(self):
        import timeline as timeline_mod
        d = tempfile.mkdtemp(prefix="tl_empty_")
        with open(os.path.join(d, "timeline.jsonl"), "w",
                  encoding="utf-8") as f:
            f.write("")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            timeline_mod.report(d)
        self.assertIn("时间线为空", buf.getvalue())
        self.assertFalse(os.path.exists(os.path.join(d, "report.md")))


class TestAutoClickEquiv(unittest.TestCase):
    """uitool.auto_click：定位→点击→(无 expect) 返回成功；定位失败走记录。"""

    def _loc(self, **kw):
        base = {"x": 100, "y": 200, "w": 0, "h": 0, "cx": 100, "cy": 200,
                "src": uitool.SourceEnum.HANDLE, "conf": 1.0,
                "chain": [uitool.SourceEnum.HANDLE.value], "hwnd": 12345}
        base.update(kw)
        return base

    def test_click_ok_without_expect(self):
        session = tempfile.mkdtemp(prefix="ac_ok_")
        os.makedirs(os.path.join(session, "shots"), exist_ok=True)
        loc = self._loc()
        with unittest.mock.patch.object(
                uitool, "_locate_target", return_value=loc), \
                unittest.mock.patch.object(uitool.env, "activate_window"), \
                unittest.mock.patch.object(uitool, "time") as tm, \
                unittest.mock.patch.object(uitool, "_sub") as sub, \
                unittest.mock.patch.object(uitool.tl.Timeline, "shot",
                                           return_value="shots/step001.png"):
            tm.sleep.return_value = None
            r = uitool.auto_click(session, text="x", hwnd=None, force_xy=None,
                                  title=None, cls=None, expect=None,
                                  retries=1)
        self.assertTrue(r["ok"])
        self.assertEqual(r["attempts"], 1)
        self.assertEqual(r["chain"], ["handle"])
        sub.assert_called_once_with(
            ["sendinput.py", "click", "100", "200"])
        with open(os.path.join(session, "timeline.jsonl"),
                  encoding="utf-8") as f:
            rows = [json.loads(x) for x in f.read().splitlines() if x.strip()]
        click_row = [x for x in rows if x["action"] == "click"][0]
        self.assertEqual(click_row["src"], "handle")
        self.assertEqual(click_row["conf"], 1.0)
        self.assertEqual(click_row["chain"], ["handle"])

    def test_locate_fail_returns_error_and_records(self):
        session = tempfile.mkdtemp(prefix="ac_fail_")
        os.makedirs(os.path.join(session, "shots"), exist_ok=True)
        with unittest.mock.patch.object(
                uitool, "_locate_target",
                side_effect=RuntimeError("拒绝裸坐标")), \
                unittest.mock.patch.object(uitool.tl.Timeline, "shot"):
            r = uitool.auto_click(session, text=None, hwnd=None,
                                  force_xy=None, title=None, cls=None,
                                  expect=None, retries=1)
        self.assertFalse(r["ok"])
        self.assertIn("拒绝裸坐标", r["error"])
        with open(os.path.join(session, "timeline.jsonl"),
                  encoding="utf-8") as f:
            rows = [json.loads(x) for x in f.read().splitlines() if x.strip()]
        self.assertEqual(rows[-1]["action"], "locate_fail")
        self.assertEqual(rows[-1]["result"], "fail")

    def test_expect_ok_returns_after_verify(self):
        session = tempfile.mkdtemp(prefix="ac_expect_")
        os.makedirs(os.path.join(session, "shots"), exist_ok=True)
        loc = self._loc()
        with unittest.mock.patch.object(
                uitool, "_locate_target", return_value=loc), \
                unittest.mock.patch.object(uitool.env, "activate_window"), \
                unittest.mock.patch.object(uitool, "time") as tm, \
                unittest.mock.patch.object(uitool, "_sub"), \
                unittest.mock.patch.object(uitool, "verify_text",
                                           return_value={"found": True}), \
                unittest.mock.patch.object(uitool.tl.Timeline, "shot",
                                           return_value="shots/step001.png"):
            tm.sleep.return_value = None
            r = uitool.auto_click(session, text="x", hwnd=None, force_xy=None,
                                  title=None, cls=None, expect="确定",
                                  retries=1)
        self.assertTrue(r["ok"])
        self.assertTrue(r["verify"]["found"])


class TestMainEnvEquiv(unittest.TestCase):
    """uitool.main env 分支：DPI/多屏 JSON 输出。"""

    def test_main_env_branch(self):
        import io
        from contextlib import redirect_stdout
        with unittest.mock.patch.object(
                uitool.env, "set_dpi_awareness"), \
                unittest.mock.patch.object(
                    uitool.env, "dpi_for_window",
                    return_value=(144, 1.25)), \
                unittest.mock.patch.object(
                    uitool.env, "monitors", return_value=[]), \
                unittest.mock.patch.object(
                    sys, "argv", ["uitool.py", "env"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                uitool.main()
        data = json.loads(buf.getvalue().strip().splitlines()[-1])
        self.assertEqual(data["dpi"], 144)
        self.assertEqual(data["scale"], 1.25)
        self.assertEqual(data["monitors"], [])
        self.assertIn("python", data)


class TestPickTargetEquiv(unittest.TestCase):
    """env.pick_target：噪声过滤 + 规则打分 + target 确定性。"""

    def _wins(self):
        return [
            {"hwnd": 1, "title": "", "class": "Shell_TrayWnd",
             "rect": [0, 0, 10, 10], "pid": 10},
            {"hwnd": 2, "title": "", "class": "Progman",
             "rect": [0, 0, 10, 10], "pid": 11},
            {"hwnd": 3, "title": "CookieSync",
             "class": "ConsoleWindowClass",
             "rect": [0, 0, 10, 10], "pid": 100},
        ]

    def test_no_rules_no_target(self):
        r = env.pick_target([], windows=self._wins())
        self.assertIsNone(r["target"])
        self.assertEqual(r["candidates"], [])

    def test_rule_hit_selects_target(self):
        r = env.pick_target([{"name": "目标", "title": "CookieSync"}],
                            windows=self._wins())
        self.assertIsNotNone(r["target"])
        self.assertEqual(r["target"]["title"], "CookieSync")
        self.assertEqual(r["target"]["score"], 10)
        self.assertIn("目标", r["target"]["reason"])
        self.assertEqual(len(r["candidates"]), 1)

    def test_all_noise_no_target(self):
        r = env.pick_target([{"name": "x", "title": "CookieSync"}],
                            windows=self._wins()[:2])
        self.assertIsNone(r["target"])
        self.assertEqual(r["candidates"], [])


class TestProcessCountEquiv(unittest.TestCase):
    """env.process_count：psutil 计数（大小写不敏感）+ 异常兜底 0。"""

    def _fake_psutil(self, procs, raise_iter=False):
        fake = unittest.mock.MagicMock()

        def _iter(attrs=None):
            if raise_iter:
                raise RuntimeError("psutil 不可用")
            return [type("P", (), {"info": p})() for p in procs]
        fake.process_iter.side_effect = _iter
        return fake

    def test_count_case_insensitive(self):
        fake = self._fake_psutil([{"name": "chrome.exe"},
                                  {"name": "Chrome.EXE"},
                                  {"name": "notepad.exe"}])
        with unittest.mock.patch.dict(sys.modules, {"psutil": fake}):
            self.assertEqual(env.process_count("chrome.exe"), 2)
            self.assertEqual(env.process_count("notepad.exe"), 1)

    def test_exception_returns_zero(self):
        fake = self._fake_psutil([], raise_iter=True)
        with unittest.mock.patch.dict(sys.modules, {"psutil": fake}):
            self.assertEqual(env.process_count("chrome.exe"), 0)


class TestPortListenEquiv(unittest.TestCase):
    """env.port_listen：psutil 主 + socket 兜底。"""

    def test_psutil_hit(self):
        fake_psutil = unittest.mock.MagicMock()
        fake_psutil.net_connections.return_value = [
            type("C", (), {"laddr": type("L", (), {"port": 8080})(),
                           "status": "LISTEN"})()]
        with unittest.mock.patch.dict(sys.modules,
                                      {"psutil": fake_psutil}):
            self.assertTrue(env.port_listen(8080))

    def test_socket_fallback_hit(self):
        fake_psutil = unittest.mock.MagicMock()
        fake_psutil.net_connections.return_value = []
        fake_socket = unittest.mock.MagicMock()
        fake_socket.create_connection.return_value = \
            unittest.mock.MagicMock()
        with unittest.mock.patch.dict(sys.modules,
                                      {"psutil": fake_psutil,
                                       "socket": fake_socket}):
            self.assertTrue(env.port_listen(8080, timeout=0.1))

    def test_both_fail_false(self):
        fake_psutil = unittest.mock.MagicMock()
        fake_psutil.net_connections.return_value = []
        fake_socket = unittest.mock.MagicMock()
        fake_socket.create_connection.side_effect = ConnectionRefusedError
        with unittest.mock.patch.dict(sys.modules,
                                      {"psutil": fake_psutil,
                                       "socket": fake_socket}):
            self.assertFalse(env.port_listen(8080, timeout=0.1))


class TestWaitWindowReadyEquiv(unittest.TestCase):
    """env.wait_window_ready：响应即 True；超时轮询返回 False。"""

    def test_responding_true(self):
        with unittest.mock.patch.object(
                env.ctypes.windll.user32, "SendMessageTimeoutW",
                return_value=1), \
                unittest.mock.patch.object(env.time, "sleep") as sl:
            self.assertTrue(env.wait_window_ready(12345, timeout=0.2))
        sl.assert_not_called()

    def test_timeout_false_after_polling(self):
        with unittest.mock.patch.object(
                env.ctypes.windll.user32, "SendMessageTimeoutW",
                return_value=0), \
                unittest.mock.patch.object(env.time, "time",
                                           side_effect=[0.0, 0.1, 0.2,
                                                        0.3, 5.1]), \
                unittest.mock.patch.object(env.time, "sleep") as sl:
            self.assertFalse(env.wait_window_ready(12345, timeout=5.0))
        self.assertEqual(sl.call_count, 3)


if __name__ == "__main__":
    unittest.main()
