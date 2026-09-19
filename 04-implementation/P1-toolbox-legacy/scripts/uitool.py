# -*- coding: utf-8 -*-
"""uitool.py — UI 自动化工具箱统一入口（三层契约：感知→动作→审计，自动闭环）。

六阶段流程：see → decide → click/wait → verify → shot，全部打时间戳落盘。
三层契约（确定性自动化，不再靠 LLM 猜）：
  感知层 see：env.pick_target 按规则自选 target_hwnd（输出依据，不猜）
  动作层 click：强制走 locate（handle > ocr > template），拒绝裸坐标
               （--force-xy 显式声明时审计记 src=manual）
  审计层 timeline：每步记录 坐标来源 src + 置信度 conf + 回退链 chain
闭环：click --expect 未命中 → diagnose → 修复(focus/遮挡/坐标) → 重试 ≤3 次

用法：
  python uitool.py see --session s01 --title CookieSync       # 感知：自选 target
  python uitool.py click --by-locate "启动浏览器" --expect "确认启动" --session s01
  python uitool.py click --hwnd 2954324 --expect "请输入选项" --session s01
  python uitool.py click --force-xy 811,205 --session s01     # 显式裸坐标（审计 manual）
  python uitool.py key 13 --session s01
  python uitool.py paste --hwnd 2954324 "中文内容" --session s01
  python uitool.py verify-text "确定" --session s01
  python uitool.py shot --session s01 --label final
  python uitool.py report s01                                 # 审计：来源归因报告
  python uitool.py env
"""
import argparse
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import time
from enum import Enum

# --- contracts 来源引导（P2-2 收尾 #1；feature flag 说明见 restore_p1_shim.py） ---
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # scripts 自身（env/shot/... 互相 import）
_IMPL = os.path.dirname(_HERE)                              # P1 遗留目录
_IMPL_ROOT = os.path.dirname(_IMPL)                         # 04-implementation
if os.environ.get("UITOOL_CONTRACTS_SOURCE", "p2").strip().lower() == "p1":
    sys.path.insert(0, _IMPL)                               # p1 模式：经 P1 目录 contracts shim（需先运行 restore_p1_shim.py）
else:
    sys.path.insert(0, os.path.join(_IMPL_ROOT, "P2-layers"))  # 默认：契约层唯一实现
import env
import shot as shot_mod
import locate as locate_mod
import timeline as tl
from contracts import SourceEnum

PY = sys.executable
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SESSION_ROOT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "timeline")


def _v(x):
    """枚举 → value（审计 chain/JSON 用）；非枚举原样。"""
    if isinstance(x, Enum):
        return x.value
    return x


def _jdefault(o):
    if isinstance(o, Enum):
        return o.value
    return str(o)


def new_session(name=None):
    if not name:
        name = time.strftime("session_%Y%m%d_%H%M%S")
    d = os.path.join(SESSION_ROOT, name)
    os.makedirs(os.path.join(d, "shots"), exist_ok=True)
    return d, name


def _sub(args):
    r = subprocess.run([PY, os.path.join(SCRIPTS, args[0])] + args[1:],
                       capture_output=True, text=True, timeout=300)
    out = r.stdout.strip()
    try:
        return json.loads(out.splitlines()[-1]) if out else {}
    except Exception:
        return {"raw": out}


def see(session, label="", title=None, cls=None):
    """感知层：全屏截图 + 窗口状态 + 按规则自选 target_hwnd（不猜）。"""
    t = tl.Timeline(session)
    shot_path = os.path.join(session, "shots", "see_%s.png" % label)
    eng = shot_mod.get_engine()
    from PIL import Image
    Image.fromarray(eng.grab()).save(shot_path)
    wins = env.find_windows(visible_only=True)
    rules = []
    if title:
        rules.append({"title": title, "name": "title=%s" % title})
    if cls:
        rules.append({"class": cls, "name": "class=%s" % cls})
    pick = env.pick_target(rules, wins)
    tgt = pick["target"]
    t.record("see", "pick_target",
             target=tgt["title"][:40] if tgt else "无规则命中",
             result="ok" if tgt else "none",
             src=SourceEnum.RULE,
             conf=float(tgt["score"]) / 10.0 if tgt else None,
             note=(tgt["reason"][:60] if tgt
                   else "候选 %d 个，无规则命中（不猜）"
                        % len(pick["candidates"])),
             chain=[SourceEnum.RULE.value])
    # BUG-2 接线（P2-2 收尾 #5）：env_adapter 探测结果入审计时间线。
    # 最小闭环：探测 → 路由结果落审计；真实注入/截图切换由 P2-3 编排层统一。
    try:
        from env_adapter.env_probe import probe_env
        _prof = probe_env(tgt["hwnd"] if tgt else None)
        t.record("see", "env_profile",
                 target=_prof.framework or "none",
                 result="ok", src=SourceEnum.RULE, conf=None,
                 note=json.dumps({"security": _prof.security,
                                  "framework": _prof.framework,
                                  "focus_reliable": _prof.focus_reliable,
                                  "input_method": _v(_prof.input_method),
                                  "capture_method": _v(_prof.capture_method),
                                  "dpi_scale": _prof.dpi_scale,
                                  "probe_ms": _prof.probe_ms},
                                 ensure_ascii=False)[:300],
                 chain=[SourceEnum.RULE.value])
    except Exception as _e:
        t.record("see", "env_profile", target="env_adapter", result="fail",
                 src=SourceEnum.RULE, conf=None, note="env_adapter 探测失败: %r" % (_e,))
    t.record("see", "snapshot", target="%d 窗口" % len(wins),
             result="ok",
             note=json.dumps([{"hwnd": c["hwnd"],
                               "title": c["title"][:24],
                               "score": c["score"],
                               "reason": c["reason"]}
                              for c in pick["candidates"][:5]],
                             ensure_ascii=False)[:300])
    return {"shot": shot_path, "windows": len(wins),
            "target": tgt, "candidates": pick["candidates"]}


def _locate_target(session, text=None, hwnd=None, title=None, cls=None,
                   force_xy=None):
    """动作层定位三路合一。拒绝裸坐标（除非 --force-xy 显式声明）。
    返回 {cx, cy, src, conf, chain, hwnd?}。"""
    if hwnd:
        r = env.window_rect(hwnd)
        return {"x": r[0], "y": r[1], "w": r[2] - r[0], "h": r[3] - r[1],
                "cx": (r[0] + r[2]) // 2, "cy": (r[1] + r[3]) // 2,
                "src": SourceEnum.HANDLE, "conf": 1.0,
                "chain": [SourceEnum.HANDLE.value], "hwnd": hwnd}
    if text:
        shot_path = os.path.join(session, "shots", "locate_ocr.png")
        eng = shot_mod.get_engine()
        from PIL import Image
        Image.fromarray(eng.grab()).save(shot_path)
        items = locate_mod.loc_by_ocr(shot_path, text)
        if items:
            it = items[0]
            return {"x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"],
                    "cx": it["cx"], "cy": it["cy"],
                    "src": SourceEnum.OCR,
                    "conf": float(it.get("confidence", 0)),
                    "chain": [SourceEnum.HANDLE.value, SourceEnum.OCR.value],
                    "text": it.get("text", "")}
    if title or cls:
        wins = locate_mod.loc_by_handle(title, cls)
        if wins:
            w = wins[0]
            return {"x": w["x"], "y": w["y"], "w": w["w"], "h": w["h"],
                    "cx": w["cx"], "cy": w["cy"],
                    "src": SourceEnum.HANDLE, "conf": 1.0,
                    "chain": [SourceEnum.HANDLE.value],
                    "hwnd": w.get("hwnd")}
    if force_xy:
        x, y = force_xy
        return {"x": x, "y": y, "w": 0, "h": 0, "cx": x, "cy": y,
                "src": SourceEnum.MANUAL, "conf": 1.0,
                "chain": [SourceEnum.MANUAL.value]}
    raise RuntimeError(
        "拒绝裸坐标：请用 --hwnd <句柄> / --by-locate <文本> / "
        "--force-xy x,y 显式声明目标")


def _diagnose_quick(loc):
    """闭环诊断：焦点 → 遮挡 → 坐标。返回 {ok, fix, fixable, detail}。"""
    hwnd = loc.get("hwnd")
    if hwnd:
        fg = int(ctypes.windll.user32.GetForegroundWindow())
        if fg != hwnd:
            return {"ok": "warn", "fix": "activate", "fixable": True,
                    "detail": "目标不在前台 (fg=0x%X != 0x%X)" % (fg, hwnd)}
    pt = ctypes.wintypes.POINT(int(loc["cx"]), int(loc["cy"]))
    top = ctypes.windll.user32.WindowFromPoint(pt)
    if hwnd and top != hwnd:
        owner = ctypes.windll.user32.GetAncestor(top, 2)
        if owner != hwnd:
            return {"ok": "warn", "fix": "topmost", "fixable": True,
                    "detail": "点击点被其他窗口遮挡 (top=0x%X)" % top}
    if hwnd:
        r = env.window_rect(hwnd)
        if not (r[0] <= loc["cx"] <= r[2] and r[1] <= loc["cy"] <= r[3]):
            return {"ok": "warn", "fix": "relocate", "fixable": True,
                    "detail": "点击点不在目标窗口 rect 内"}
    return {"ok": True, "fix": None, "fixable": False,
            "detail": "焦点/遮挡/坐标均正常，需人工介入"}


def auto_click(session, text, hwnd, force_xy, title, cls, expect,
               retries=3, label=""):
    """动作层闭环：定位 → 点击 → 期望验证 → 失败诊断 → 修复 → 重试。"""
    t = tl.Timeline(session)
    chain = []
    last_diag = None
    for attempt in range(1, retries + 1):
        try:
            loc = _locate_target(session, text, hwnd, title, cls, force_xy)
        except RuntimeError as e:
            t.record("decide", "locate_fail", target=str(e), result="fail",
                     src=None, chain=list(chain))
            return {"ok": False, "error": str(e)}
        chain.append(_v(loc["src"]))
        t.record("click", "click",
                 target="%d,%d [%s]" % (loc["cx"], loc["cy"], loc["src"]),
                 method="sendinput", src=loc["src"], conf=loc["conf"],
                 chain=list(chain))
        if loc.get("hwnd"):
            env.activate_window(loc["hwnd"])
            time.sleep(0.6)
        _sub(["sendinput.py", "click", str(loc["cx"]), str(loc["cy"])])
        time.sleep(0.4)
        ev = t.shot()
        t.record("verify", "shot", target=ev, method="dxcam",
                 src=loc["src"], chain=list(chain))
        if not expect:
            return {"ok": True, "loc": loc, "shot": ev,
                    "attempts": attempt, "chain": chain}
        region = None
        if loc.get("hwnd"):
            r = env.window_rect(loc["hwnd"])
            region = "%d,%d,%d,%d" % (r[0], r[1], r[2] - r[0], r[3] - r[1])
        v = verify_text(session, expect, region=region)
        if v["found"]:
            t.record("verify", "expect_ok", target=expect, result="ok",
                     src=SourceEnum.OCR, chain=list(chain))
            return {"ok": True, "loc": loc, "verify": v, "shot": ev,
                    "attempts": attempt, "chain": chain}
        t.record("verify", "expect_fail", target=expect, result="fail",
                 src=SourceEnum.OCR, chain=list(chain))
        last_diag = _diagnose_quick(loc)
        chain.append("diag:" + str(last_diag.get("fix")
                                   or ("blocked"
                                       if not last_diag.get("fixable")
                                       else "manual")))
        t.record("diagnose", "diagnose", target=expect,
                 result=last_diag["ok"], src=SourceEnum.DIAGNOSE,
                 chain=list(chain), note=last_diag["detail"][:120])
        if not last_diag.get("fixable"):
            break
        fix = last_diag["fix"]
        if fix == "activate" and loc.get("hwnd"):
            env.activate_window(loc["hwnd"])
            time.sleep(0.6)
        elif fix == "topmost" and loc.get("hwnd"):
            ctypes.windll.user32.SetWindowPos(
                loc["hwnd"], -1, 0, 0, 0, 0, 19)
            time.sleep(0.5)
        elif fix == "relocate":
            pass
        time.sleep(0.5)
    return {"ok": False,
            "error": "重试 %d 次后仍未命中期望文本: %s" % (retries, expect),
            "chain": chain, "last_diag": last_diag}


def click(session, x, y, dbl=False, label=""):
    """旧接口保留（内部仍走时间线；来源由调用方显式声明）。"""
    t = tl.Timeline(session)
    t.record("click", "dblclick" if dbl else "click", "%d,%d" % (x, y),
             method="sendinput", src=SourceEnum.MANUAL, conf=1.0,
             chain=[SourceEnum.MANUAL.value])
    _sub(["sendinput.py", "dblclick" if dbl else "click",
          str(x), str(y)])
    time.sleep(0.3)
    ev = t.shot()
    t.record("verify", "shot", target=ev, method="dxcam",
             src=SourceEnum.MANUAL, chain=[SourceEnum.MANUAL.value])
    return ev


def paste(session, x, y, text, src=None):
    t = tl.Timeline(session)
    t.record("click", "paste", "%d,%d %s" % (x, y, text[:20]),
             method="clipboard+ctrl+v", src=src, conf=1.0,
             chain=[_v(src)])
    _sub(["sendinput.py", "clip", text])
    _sub(["sendinput.py", "click", str(x), str(y)])
    _sub(["sendinput.py", "hotkey", "0x11,0x41"])
    _sub(["sendinput.py", "hotkey", "0x11,0x56"])
    time.sleep(0.3)
    return t.shot()


def verify_text(session, text, region=None):
    """验证：全屏截图 → OCR 找文本（界面是否出现期望状态）。"""
    t = tl.Timeline(session)
    shot_path = os.path.join(session, "shots", "verify.png")
    eng = shot_mod.get_engine()
    from PIL import Image
    Image.fromarray(eng.grab()).save(shot_path)
    cmd = ["ocr.py", "--image", shot_path]
    if text:
        cmd += ["--filter", text]
    if region:
        cmd += ["--region", region]
    items = _sub(cmd)
    hits = items.get("items", []) if items else []
    conf = max([float(h.get("confidence", 0)) for h in hits],
               default=0)
    t.record("verify", "ocr_result", target=text,
             result="ok" if hits else "fail",
             src=SourceEnum.OCR, conf=conf,
             note="命中 %d 处" % len(hits),
             chain=[SourceEnum.OCR.value])
    return {"found": len(hits) > 0, "items": hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["see", "click", "dblclick", "key",
                                    "paste", "verify-text", "shot",
                                    "report", "env"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--session", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--html", default=None)
    ap.add_argument("--title", default=None, help="感知/定位：窗口标题子串")
    ap.add_argument("--class", dest="cls", default=None,
                    help="感知/定位：窗口类名")
    ap.add_argument("--hwnd", type=lambda s: int(s, 0), default=None,
                    help="动作层：句柄定位（精确控件，优先）")
    ap.add_argument("--by-locate", dest="by_locate", default=None,
                    help="动作层：OCR 文本定位")
    ap.add_argument("--force-xy", default=None,
                    help="动作层：显式裸坐标 x,y（审计记 src=manual）")
    ap.add_argument("--expect", default=None,
                    help="闭环：点击后期望出现的文本（未命中→诊断→重试）")
    ap.add_argument("--retries", type=int, default=3)
    a = ap.parse_args()

    session, name = (new_session(a.session)
                     if a.cmd != "report" else (a.session, a.session))
    if a.cmd == "see":
        r = see(session, a.label, a.title, a.cls)
        print(json.dumps(r, ensure_ascii=False, default=_jdefault))
    elif a.cmd == "click":
        force_xy = None
        if a.force_xy:
            fx, fy = a.force_xy.split(",")
            force_xy = (int(fx), int(fy))
        if not (a.by_locate or a.hwnd or a.title or a.cls or force_xy):
            if a.args and len(a.args) >= 2:
                print(json.dumps({
                    "ok": False,
                    "error": "拒绝裸坐标：请用 --hwnd / --by-locate <文本> "
                             "/ --force-xy x,y 显式声明目标",
                    "hint": "python uitool.py click --by-locate "
                            "'启动浏览器' --expect '确认启动'"},
                    ensure_ascii=False))
                return
            print(json.dumps({"ok": False, "error": "缺少定位参数"},
                             ensure_ascii=False))
            return
        r = auto_click(session, a.by_locate, a.hwnd, force_xy,
                       a.title, a.cls, a.expect, a.retries, a.label)
        print(json.dumps(r, ensure_ascii=False, default=_jdefault))
    elif a.cmd == "dblclick":
        if a.args and len(a.args) >= 2 \
                and not (a.by_locate or a.hwnd or a.force_xy):
            x, y = int(a.args[0]), int(a.args[1])
            print(json.dumps({"shot": click(session, x, y, dbl=True,
                                            label=a.label)},
                             ensure_ascii=False))
        else:
            fx, fy = (a.force_xy.split(",")
                      if a.force_xy else (None, None))
            force_xy = (int(fx), int(fy)) if fx else None
            r = auto_click(session, a.by_locate, a.hwnd, force_xy,
                           a.title, a.cls, a.expect, a.retries, a.label)
            print(json.dumps(r, ensure_ascii=False, default=_jdefault))
    elif a.cmd == "key":
        _sub(["sendinput.py", "key", a.args[0]])
        print("ok")
    elif a.cmd == "paste":
        if a.hwnd:
            loc = _locate_target(session, hwnd=a.hwnd)
            text = " ".join(a.args)
            r = paste(session, loc["cx"], loc["cy"], text, src=loc["src"])
            print(json.dumps({"shot": r, "loc": loc},
                             ensure_ascii=False, default=_jdefault))
        else:
            x, y = int(a.args[0]), int(a.args[1])
            text = " ".join(a.args[2:])
            print(json.dumps({"shot": paste(session, x, y, text)},
                             ensure_ascii=False))
    elif a.cmd == "verify-text":
        print(json.dumps(verify_text(session,
                                     a.args[0] if a.args else None),
                         ensure_ascii=False))
    elif a.cmd == "shot":
        t = tl.Timeline(session)
        t.record("shot", "shot", target=a.label, method="dxcam")
        p = t.shot(label=a.label)
        print(json.dumps({"shot": p}, ensure_ascii=False))
    if a.cmd == "report":
        sess = a.args[0] if a.args else a.session
        full = os.path.join(SESSION_ROOT, sess) \
            if not os.path.isabs(sess) else sess
        tl.report(full, a.html)
    elif a.cmd == "env":
        env.set_dpi_awareness()
        dpi, scale = env.dpi_for_window()
        print(json.dumps({"dpi": dpi, "scale": scale,
                          "monitors": [m.to_dict() for m in env.monitors()],
                          "python": sys.version.split()[0]},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
