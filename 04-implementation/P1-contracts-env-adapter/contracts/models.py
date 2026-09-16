# -*- coding: utf-8 -*-
"""contracts/models.py — 统一数据模型（8 个核心模型 + 辅助模型）。

所有脚本跨层传数据一律使用本模块类型，禁止自定义同义结构。
坐标一律物理像素，bbox 格式 [left, top, right, bottom]。
"""
from dataclasses import dataclass, field
from typing import Optional

from .enums import CaptureMethod, ErrorCode, InputMethod, SourceEnum, VerifyLevel


@dataclass
class TraceSpan:
    trace_id: str
    layer: str
    step: str
    ts_start: float
    ts_end: float
    meta: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return round((self.ts_end - self.ts_start) * 1000, 2)


@dataclass
class WindowInfo:
    hwnd: int
    title: str = ""
    pid: int = 0
    rect: tuple = (0, 0, 0, 0)          # 物理像素 [left, top, right, bottom]


@dataclass
class EnvProfile:
    version: int = 1
    browser: Optional[str] = None       # chrome / 360se / msedge / electron / None
    framework: Optional[str] = None     # wujie / iframe / native / None
    iframe: bool = False
    security: Optional[str] = None      # 拦截鼠标的安全软件名 / None
    dpi_scale: float = 1.0
    integrity_level: str = "medium"     # high / medium / low
    input_method: InputMethod = InputMethod.SEND_INPUT
    capture_method: CaptureMethod = CaptureMethod.DXCAM
    focus_reliable: bool = True
    probe_ms: float = 0.0
    probed_at: float = 0.0


@dataclass
class Element:
    id: str                             # 三层指纹 elem_s:{hash}_p:{path}_h:{handle}
    type: str = "button"                # button / input / text_area / icon / text
    text: Optional[str] = None
    bbox_phys: tuple = (0, 0, 0, 0)
    bbox_logic: tuple = (0, 0, 0, 0)
    handle: Optional[int] = None
    source: SourceEnum = SourceEnum.UIA
    confidence: float = 0.0
    parent_id: Optional[str] = None
    children_ids: list = field(default_factory=list)


@dataclass
class OcrItem:
    text: str = ""
    bbox_phys: tuple = (0, 0, 0, 0)
    confidence: float = 0.0


@dataclass
class StateSnapshot:
    trace_id: str = ""
    timestamp: float = 0.0
    env: Optional[EnvProfile] = None
    window: Optional[WindowInfo] = None
    elements: list = field(default_factory=list)
    ocr: list = field(default_factory=list)         # 仅校验，不做坐标来源
    layout_tree: dict = field(default_factory=dict)
    visual_features: dict = field(default_factory=dict)
    state_hash: str = ""


@dataclass
class ActionIntent:
    intent: str = "click"               # ActionType 值；LLM 输出，不含坐标
    target_element_id: Optional[str] = None
    text: Optional[str] = None
    reason: str = ""
    fallback: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ResolvedAction:
    action: str = "click"               # ActionType 值
    target: Optional[str] = None
    handle: Optional[int] = None
    bbox_phys: tuple = (0, 0, 0, 0)
    click_point_phys: tuple = (0, 0)
    method: SourceEnum = SourceEnum.HANDLE   # 定位来源（handle/uia/cache/...）
    fallback_points: list = field(default_factory=list)
    idempotent: bool = True
    input_method: Optional[InputMethod] = None


@dataclass
class ExecutionResult:
    trace_id: str = ""
    action: str = ""
    status: str = "success"             # success / failed / skipped
    duration_ms: float = 0.0
    retries: int = 0
    error: Optional[ErrorCode] = None
    screenshot_before: str = ""
    screenshot_after: str = ""


@dataclass
class VerificationResult:
    trace_id: str = ""
    action: str = ""
    level: VerifyLevel = VerifyLevel.WEAK
    status: str = "passed"              # passed / failed / skipped
    method: str = ""                    # state_diff / ocr_check / screenshot_diff / business_assert
    detail: dict = field(default_factory=dict)
    screenshot: Optional[str] = None
    retries: int = 0                    # 本次动作已重试次数（select_flow HUMAN 判定依据）


@dataclass
class StateDiff:
    significant: bool = False
    changed_elements: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class Rule:
    name: str = ""
    text: str = ""
    title: str = ""
    cls: str = ""
    offset: tuple = (0, 0)
    action: str = "none"
    ts: float = 0.0


@dataclass
class ResourceSnapshot:
    cpu_percent: float = 0.0
    gpu_util: float = 0.0
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    mem_mb: int = 0
    fps: float = 0.0
    queue_len: int = 0


@dataclass
class FallbackAction:
    action: str = ""                    # 降级动作（switch_input / activate_window / human ...）
    target: str = ""
    note: str = ""
    source: str = "fallback_policy"
