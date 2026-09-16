# -*- coding: utf-8 -*-
"""cache.py — 本地缓存层：业务指令 / 元素规则 / 句柄位置 / 阈值配置。

减少云端与 OCR 重复请求：
  - ops:    常用业务操作指令序列（业务流程缓存），命中后按序执行
  - rules:  元素匹配规则 {text/title/class/offset/action}，定位命中即缓存坐标
  - hwnds:  句柄位置缓存 {hwnd, rect, ts}；操作前比对 GetWindowRect，
            移动超过阈值才重新定位（句柄移动判断，阈值开关）
  - config: 阈值配置（move_px 移动判定、sim 模板相似度、ocr_conf 置信度）

用法：
  python cache.py ops save flow1 '["activate 123","click 100,200"]'
  python cache.py ops get flow1
  python cache.py rule add 豆包AI提示 '{"text":"豆包AI","offset":[0,0],"action":"none"}'
  python cache.py rule hit "豆包AI提示"
  python cache.py hwnd save 123456 100,200,300,400
  python cache.py hwnd moved 123456        # 返回 moved|same
  python cache.py config set move_px 8
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "cache")
OPS_FILE = os.path.join(CACHE_DIR, "ops.json")
RULES_FILE = os.path.join(CACHE_DIR, "rules.json")
HWNDS_FILE = os.path.join(CACHE_DIR, "hwnds.json")
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")

DEFAULT_CONFIG = {"move_px": 8, "sim_threshold": 0.8,
                  "ocr_conf": 0.6, "hwnd_ttl_s": 300}


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save(path, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def config():
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(_load(CONFIG_FILE, {}))
    return cfg


def set_config(key, value):
    cfg = config()
    cfg[key] = value
    _save(CONFIG_FILE, cfg)
    return cfg


# ---------- 业务指令缓存 ----------
def ops_save(name, steps):
    data = _load(OPS_FILE, {})
    data[name] = {"steps": steps, "ts": time.time()}
    _save(OPS_FILE, data)
    return len(steps)


def ops_get(name):
    return _load(OPS_FILE, {}).get(name)


def ops_list():
    return list(_load(OPS_FILE, {}).keys())


# ---------- 元素规则缓存 ----------
def rule_add(name, rule):
    data = _load(RULES_FILE, {})
    data[name] = dict(rule)
    data[name]["ts"] = time.time()
    _save(RULES_FILE, data)
    return True


def rule_get(name):
    return _load(RULES_FILE, {}).get(name)


def rules_list():
    return _load(RULES_FILE, {})


# ---------- 句柄位置缓存（移动判断） ----------
def hwnd_save(hwnd, rect):
    data = _load(HWNDS_FILE, {})
    data[str(hwnd)] = {"rect": list(rect), "ts": time.time()}
    _save(HWNDS_FILE, data)
    return True


def hwnd_moved(hwnd, move_px=None):
    """判断窗口相对缓存是否移动/变化。返回 "same" | "moved" | "unknown"。"""
    cfg = config()
    move_px = move_px if move_px is not None else cfg["move_px"]
    cached = _load(HWNDS_FILE, {}).get(str(hwnd))
    if not cached:
        return "unknown"
    try:
        cur = env.window_rect(hwnd)
    except Exception:
        return "unknown"
    old = cached["rect"]
    delta = max(abs(cur[0] - old[0]), abs(cur[1] - old[1]),
                abs(cur[2] - old[2]), abs(cur[3] - old[3]))
    if delta > move_px:
        return "moved"
    return "same"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ops", "rule", "hwnd", "config"])
    ap.add_argument("sub", nargs="*")
    a, unknown = ap.parse_known_args()
    a.sub = a.sub + unknown

    if a.cmd == "ops" and a.sub[0] == "save":
        name, steps_json = a.sub[1], a.sub[2]
        if steps_json == "--file":
            with open(a.sub[3], encoding="utf-8-sig") as f:
                steps_json = f.read()
        n = ops_save(name, json.loads(steps_json))
        print("ok 已缓存 %d 步: %s" % (n, name))
    elif a.cmd == "ops" and a.sub[0] == "get":
        print(json.dumps(ops_get(a.sub[1]), ensure_ascii=False))
    elif a.cmd == "ops" and a.sub[0] == "list":
        print(json.dumps(ops_list(), ensure_ascii=False))
    elif a.cmd == "rule" and a.sub[0] == "add":
        name, rule_json = a.sub[1], a.sub[2]
        if rule_json == "--file":
            with open(a.sub[3], encoding="utf-8") as f:
                rule_json = f.read()
        rule_add(name, json.loads(rule_json))
        print("ok 规则已缓存: %s" % name)
    elif a.cmd == "rule" and a.sub[0] == "get":
        print(json.dumps(rule_get(a.sub[1]), ensure_ascii=False))
    elif a.cmd == "hwnd" and a.sub[0] == "save":
        hwnd, rect = int(a.sub[1]), [int(v) for v in a.sub[2].split(",")]
        hwnd_save(hwnd, rect)
        print("ok 句柄位置已缓存")
    elif a.cmd == "hwnd" and a.sub[0] == "moved":
        print(hwnd_moved(int(a.sub[1])))
    elif a.cmd == "config" and a.sub[0] == "set":
        k, v = a.sub[1], a.sub[2]
        if v.lower() in ("true", "false"):
            v = v.lower() == "true"
        else:
            try:
                v = float(v)
            except ValueError:
                pass
        set_config(k, v)
        print("ok %s=%s" % (k, v))


if __name__ == "__main__":
    main()
