# -*- coding: utf-8 -*-
"""contracts/state_hash.py — 状态哈希（决策缓存键）。

规格（用户评分 + v3）：
  参与字段：target_hint 圈定的目标元素 + 输入框 + 按钮，每类上限 8
  位置量化：2% 网格（窗口宽高 50 格）
  文本规范化：去空白 + 全角→半角（NFKC）+ 小写
  不参与：ocr / visual_features / 原始坐标精确值 / trace 元数据
  碰撞后二次校验：由调用方（决策缓存）比对元素实时指纹，任一失效即视为未命中
"""
import hashlib
import unicodedata

_GRID = 50                       # 2% 网格
_KINDS = ("button", "input", "text_area")


def normalize_text(s) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return " ".join(s.split()).lower()


def grid_cell(v, span) -> int:
    """位置量化到 2% 网格。span<=0 时返回 0。"""
    if span <= 0:
        return 0
    return min(int(v / span * _GRID), _GRID - 1)


def select_key_elements(elements, target_hint=None, max_per_type=8):
    """关键元素选择规则（显式）：
      target_hint 非空：取 id == target_hint 的元素 + 所有输入框；集合为空回退全量
      为空：全部 button/input/text_area
      每类上限 max_per_type（按出现顺序截断）
    """
    base = [e for e in elements if getattr(e, "type", "") in _KINDS]
    if target_hint:
        key = [e for e in base if getattr(e, "id", "") == target_hint] + \
              [e for e in base if getattr(e, "type", "") == "input"]
        if not key:
            key = list(base)
    else:
        key = list(base)
    out, counts = [], {}
    for e in key:
        t = getattr(e, "type", "")
        if counts.get(t, 0) >= max_per_type:
            continue
        counts[t] = counts.get(t, 0) + 1
        out.append(e)
    return out


def state_hash(snapshot, target_hint=None) -> str:
    """按规格计算状态哈希。snapshot 需含 elements 与 window（rect/title）。"""
    elems = select_key_elements(getattr(snapshot, "elements", None) or [],
                                target_hint)
    win = getattr(snapshot, "window", None)
    win_w = win_h = 1
    title = ""
    if win is not None:
        r = win.rect or (0, 0, 0, 0)
        win_w = max(r[2] - r[0], 1)
        win_h = max(r[3] - r[1], 1)
        title = normalize_text(getattr(win, "title", ""))
    parts = []
    for e in elems:
        b = e.bbox_phys or (0, 0, 0, 0)
        parts.append("%s:%s:%d:%d" % (
            e.type, normalize_text(e.text),
            grid_cell(b[0], win_w), grid_cell(b[1], win_h)))
    parts.append(title)
    parts.sort()
    return hashlib.sha1("\n".join(parts).encode("utf-8", "replace")).hexdigest()
