# -*- coding: utf-8 -*-
"""contracts/stable_id.py — 元素指纹：三层可分解，两个用途独立解析。

格式：elem_s:{semantic}_p:{control_path}_h:{handle}
  语义段 semantic：{hash} 或 {hash}_{label}（label 用于碰撞消歧）
  空段一律写 none（禁止双下划线等自造空段记号）。

用途区分（用户评分规格）：
  定位用 resolve_for_action：L1 handle > L2 control_path > L3 semantic
  缓存键用 resolve_for_cache：L3 semantic > L2 control_path > L1 handle
  两个用途独立函数，哪层失效回退哪层，单段失效不拉垮其他层。
"""
import re

EMPTY = "none"
_PREFIX = "elem_s:"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{4,12}$")


def _fmt(s):
    return s if s else EMPTY


def element_id(semantic_hash=None, control_path=None, handle=None,
               disambiguator=None) -> str:
    """生成三层指纹。空段自动写 none。disambiguator 追加消歧标签（碰撞时用）。"""
    sem = _fmt(semantic_hash)
    if disambiguator:
        sem = "%s_%s" % (sem, disambiguator)
    path = _fmt(control_path)
    h = _fmt(hex(handle) if isinstance(handle, int) else handle)
    return "%s%s_p:%s_h:%s" % (_PREFIX, sem, path, h)


def parse_element_id(eid: str) -> dict:
    """解析指纹 → {semantic, semantic_hash, disambiguator, control_path, handle}。
    格式非法抛 ValueError。"""
    if not eid or not eid.startswith(_PREFIX):
        raise ValueError("非法元素 id（缺前缀 elem_s:）: %r" % eid)
    body = eid[len(_PREFIX):]
    seg = body.split("_p:")
    if len(seg) != 2 or "_h:" not in seg[1]:
        raise ValueError("非法元素 id（缺 _p:/_h: 段）: %r" % eid)
    sem_seg = seg[0]
    rest = seg[1].split("_h:", 1)
    path_seg, h_seg = rest[0], rest[1]

    semantic = None if sem_seg == EMPTY else sem_seg
    semantic_hash, disambiguator = None, None
    if semantic is not None and "_" in semantic:
        h_part, label = semantic.split("_", 1)
        if _HASH_RE.match(h_part):
            semantic_hash, disambiguator = h_part, label
        # 非 hash 前缀的语义段整体保留（如纯文本锚点）
    elif semantic is not None and _HASH_RE.match(semantic):
        semantic_hash = semantic

    path = None if path_seg == EMPTY else path_seg
    handle = None
    if h_seg != EMPTY:
        try:
            handle = int(h_seg, 16)
        except ValueError:
            raise ValueError("非法 handle 段: %r" % h_seg)
    return {"semantic": semantic, "semantic_hash": semantic_hash,
            "disambiguator": disambiguator, "control_path": path,
            "handle": handle}


def resolve_for_action(eid: str) -> list:
    """定位用：按 L1 handle > L2 control_path > L3 semantic 返回可用层。
    返回 [(layer, value), ...]，调用方逐层尝试。"""
    p = parse_element_id(eid)
    out = []
    if p["handle"] is not None:
        out.append(("handle", p["handle"]))
    if p["control_path"] is not None:
        out.append(("control_path", p["control_path"]))
    if p["semantic"] is not None:
        out.append(("semantic", p["semantic"]))
    return out


def resolve_for_cache(eid: str) -> list:
    """缓存键用：按 L3 semantic > L2 control_path > L1 handle 返回可用层。"""
    p = parse_element_id(eid)
    out = []
    if p["semantic"] is not None:
        out.append(("semantic", p["semantic"]))
    if p["control_path"] is not None:
        out.append(("control_path", p["control_path"]))
    if p["handle"] is not None:
        out.append(("handle", p["handle"]))
    return out
