# -*- coding: utf-8 -*-
"""env_adapter/fallback_policy.py — 声明式降级策略表。

唯一降级入口：新增环境 = 加一行表项；代码中出现 if wujie: 等判断视为违规。
"""
from contracts import EnvProfile, ErrorCode, FallbackAction

FALLBACK_TABLE = [
    {"env": "wujie", "error": ErrorCode.INPUT_FAILED,
     "action": "switch_input", "target": "handle_post",
     "note": "wujie 拦截 SendInput 鼠标，切换句柄直投"},
    {"env": "wujie", "error": ErrorCode.FOCUS_LOST,
     "action": "activate_window", "target": "retry",
     "note": "远程软件接管导致焦点丢失，重激活"},
    {"env": "*", "error": ErrorCode.FOCUS_LOST,
     "action": "activate_window", "target": "retry",
     "note": "前台被抢占（如 Chrome），重激活目标窗口"},
    {"env": "*", "error": ErrorCode.OCCLUDED,
     "action": "minimize_foreground", "target": "retry",
     "note": "点击点被其他窗口遮挡，最小化遮挡窗口"},
    {"env": "*", "error": ErrorCode.ENV_UNSUPPORTED,
     "action": "switch_capture", "target": "mss",
     "note": "dxcam 瞬断，切换 mss 兜底"},
    {"env": "*", "error": ErrorCode.NON_IDEMPOTENT_RETRY,
     "action": "human", "target": "pause",
     "note": "不可重试操作禁止自动重试，转人工"},
]


def resolve(env: EnvProfile | None, error_code: ErrorCode) -> FallbackAction | None:
    """按 环境特征 × 错误码 查降级动作。无命中返回 None（由调用方上报）。"""
    for row in FALLBACK_TABLE:
        if row["error"] != error_code:
            continue
        if row["env"] != "*" and (env is None
                                  or row["env"] not in (env.framework or "")):
            continue
        return FallbackAction(action=row["action"], target=row["target"],
                              note=row["note"])
    return None
