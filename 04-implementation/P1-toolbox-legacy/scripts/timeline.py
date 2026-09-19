# -*- coding: utf-8 -*-
"""timeline.py — 审计时间线：每步 截图+时间戳+动作+结果 自动落盘，可回放/可审计/可对比基线。

数据结构（timeline.jsonl，每行一个事件）：
{
  "ts": "2026-09-16T04:20:00.123+08:00",   # 动作发出时刻（毫秒精度）
  "phase": "see|decide|click|wait|verify|shot",  # 六阶段
  "step": 12,                                # 步序号
  "action": "click", "target": "...",        # 动作与对象
  "method": "sendinput|clipboard|handle",    # 注入方式
  "result": "ok|fail|timeout",               # 结果
  "latency_ms": 87,                          # 距上一步的延迟
  "evidence": "shots/step12.png",            # 证据截图相对路径
  "note": ""                                 # 补充说明
}
"""
import argparse
import glob
import json
import os
import sys
import time
from time import perf_counter as _pc

# --- contracts 来源引导（P2-2 收尾 #1；feature flag 说明见 restore_p1_shim.py） ---
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # scripts 自身（env/shot/... 互相 import）
_IMPL = os.path.dirname(_HERE)                              # P1 遗留目录
_IMPL_ROOT = os.path.dirname(_IMPL)                         # 04-implementation
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _IMPL)                               # p1 模式：经 P1 目录 contracts shim（需先运行 restore_p1_shim.py）
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))  # 默认：契约层唯一实现
from contracts import SourceEnum


def now_iso():
    t = time.time()
    return (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
            + ".%03d" % int((t % 1) * 1000)
            + time.strftime("%z", time.localtime(t)))


class Timeline:
    def __init__(self, session_dir, session_name=None):
        self.root = session_dir
        self.shots_dir = os.path.join(session_dir, "shots")
        os.makedirs(self.shots_dir, exist_ok=True)
        self.jsonl = os.path.join(session_dir, "timeline.jsonl")
        self.session = session_name or time.strftime("session_%Y%m%d_%H%M%S")
        self._t0 = _pc()
        self._last_pc = None
        self.step = 0

    def record(self, phase, action, target="", method="", result="ok",
               note="", latency_ms=None, src=None, conf=None, chain=None):
        """记录事件。审计归因字段：
        src   坐标/目标来源: handle|template|ocr|rule|manual|diagnose
        conf  置信度 0-1（manual 恒记 1 但注明来源，便于审计）
        chain 回退链/诊断链: ["handle","ocr"] 或 ["focus","coords","retry"]"""
        self.step += 1
        ev = {
            "ts": now_iso(),
            "phase": phase,
            "step": self.step,
            "action": action,
            "target": target,
            "method": method,
            "result": result,
            "latency_ms": latency_ms if latency_ms is not None
                          else self._delta_ms(),
            "src": src.value if isinstance(src, SourceEnum) else src,
            "conf": conf,
            "chain": chain or [],
            "note": note,
        }
        with open(self.jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self._last_pc = _pc()
        return ev

    def _delta_ms(self):
        if self._last_pc is None:
            return 0
        return int((_pc() - self._last_pc) * 1000)

    def shot(self, step=None, label=""):
        """保存当前全屏截图到 shots/，返回相对路径。复用模块级单例引擎。"""
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import shot as shot_mod
        eng = shot_mod.get_engine()
        img = eng.grab()
        from PIL import Image
        name = "step%03d%s.png" % (
            step if step else self.step,
            "_" + label if label else "")
        path = os.path.join(self.shots_dir, name)
        Image.fromarray(img).save(path)
        return os.path.relpath(path, self.root)


def load(session_dir):
    rows = []
    p = os.path.join(session_dir, "timeline.jsonl")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def report(session_dir, out_html=None):
    """生成可回放审计报告（Markdown + HTML 可选）。"""
    rows = load(session_dir)
    if not rows:
        print("时间线为空")
        return
    md = [
        "# UI 自动化审计报告",
        "",
        "- 会话: %s" % session_dir,
        "- 步数: %d" % len(rows),
        "- 起止: %s → %s" % (rows[0]["ts"], rows[-1]["ts"]),
        "",
        "## 事件明细",
        "",
        "| # | 阶段 | 动作 | 目标 | 来源 | 置信度 | 回退链 | 方式 | 结果 | 延迟ms | 截图 |",
        "|---|------|------|------|------|--------|--------|------|------|--------|------|",
    ]
    for r in rows:
        src = r.get("src") or "-"
        conf = r.get("conf")
        conf_s = "-" if conf is None else "%.2f" % conf
        chain = ",".join(r.get("chain") or []) or "-"
        ev = "-"
        if r.get("evidence"):
            ev = "[查看](%s)" % r["evidence"]
        md.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["step"], r["phase"], r["action"],
            r["target"] or "-", src, conf_s, chain,
            r["method"] or "-", r["result"],
            r.get("latency_ms", "-"), ev))
    md.append("")

    # 分阶段延迟统计
    phases = {}
    for r in rows:
        if r.get("latency_ms") is None:
            continue
        phases.setdefault(r.get("phase", "?"), []).append(r["latency_ms"])
    if phases:
        md.append("## 分阶段延迟统计（ms）")
        md.append("")
        md.append("| 阶段 | 次数 | mean | P50 | P95 | max |")
        md.append("|------|------|------|-----|-----|-----|")
        for ph, vals in sorted(phases.items()):
            v = sorted(vals)
            mean = sum(v) / len(v)
            p50 = v[(len(v) - 1) // 2]
            p95 = v[min(int(len(v) * 0.95), len(v) - 1)]
            md.append("| %s | %d | %.1f | %.1f | %.1f | %d |" % (
                ph, len(v), mean, p50, p95, max(v)))
        md.append("")

    # 延迟异常检测（>2s 标黄）
    slow = [r for r in rows if r.get("latency_ms")
            and r["latency_ms"] > 2000]
    if slow:
        md.append("## 延迟异常（>2s，卡顿/卡点自暴露）")
        for r in slow:
            md.append("- 步骤 %d %s→%s: %d ms" % (
                r["step"], r.get("phase", ""), r.get("action", ""),
                r["latency_ms"]))
        md.append("")

    # 坐标来源分布（归因）
    srcs = {}
    for r in rows:
        if not r.get("src"):
            continue
        s = r["src"]
        try:
            s = SourceEnum(s).name
        except ValueError:
            pass
        srcs[s] = srcs.get(s, 0) + 1
    if srcs:
        md.append("## 坐标来源分布（归因）")
        md.append("")
        md.append("| 来源 | 次数 |")
        md.append("|------|------|")
        for k, v in sorted(srcs.items(), key=lambda x: -x[1]):
            md.append("| %s | %d |" % (k, v))
        md.append("")

    md_path = os.path.join(session_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    if out_html:
        html = ["<!doctype html><meta charset='utf-8'><title>审计报告</title>",
                "<style>body{font-family:system-ui;margin:24px;color:#222}"
                "table{border-collapse:collapse}td,th{border:1px solid #ccc;"
                "padding:4px 8px;font-size:13px}img{max-width:280px;"
                "border:1px solid #ddd;margin:2px}</style>",
                "<h1>UI 自动化审计报告</h1>",
                "<p>%s · %d 步 · %s → %s</p>" % (
                    session_dir, len(rows), rows[0]["ts"], rows[-1]["ts"]),
                "<table><tr><th>#</th><th>阶段</th><th>动作</th><th>目标</th>"
                "<th>来源</th><th>置信度</th><th>回退链</th><th>方式</th>"
                "<th>结果</th><th>延迟ms</th><th>证据</th></tr>"]
        for r in rows:
            ev = ""
            if r.get("evidence"):
                ev = ("<img src='%s' title='step %d %s'>"
                      % (r["evidence"], r["step"], r["action"]))
            html.append("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td>"
                        "<td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                        "<td>%s</td><td>%s</td><td>%s</td></tr>" % (
                            r["step"], r.get("phase", ""), r["action"],
                            r.get("target", ""), r.get("src", "-"),
                            r.get("conf", "-"),
                            ",".join(r.get("chain") or []),
                            r.get("method", ""), r.get("result", ""),
                            r.get("latency_ms", ""), ev))
        html.append("</table></body>")
        with open(out_html, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        print("报告已生成: %s / %s" % (md_path, out_html))
    else:
        print("报告已生成: %s" % md_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["report"])
    ap.add_argument("session")
    ap.add_argument("--html", default=None)
    a = ap.parse_args()
    if a.cmd == "report":
        report(a.session, a.html)
