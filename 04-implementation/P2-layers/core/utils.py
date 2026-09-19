# -*- coding: utf-8 -*-
"""core/utils.py — 公共工具函数（P2-3 单源化落点）。

每一项都对应《P2-3 单源化清单》里一处"多处各自实现"的能力，
迁入后被 contracts / env_adapter / scripts / testbar-console 共同引用。

| # | 能力 | 此前实现位置 |
|---|---|---|
| 1 | `jdefault` / `jdumps` | locate.py::_jdefault、uitool.py::_jdefault（两份且已漂移） |
| 2 | `KEY_MAP` / `key_name` / `vk_of` | testbar.py（72-95 行）；sendinput.py 无名字映射 |
| 3 | `pids_by_name` / `proc_running` / `find_pid_by_name` | testbar.proc_running、perfmon.find_pid_by_name、env.process_count（三处各自遍历） |
| 4 | `remote_tools_running` | testbar.remote_tools_running（名单见 core.constants） |
| 5 | `proc_stats` | perfmon.process_times / process_memory_mb（自写 FILETIME+PSAPI，改用 psutil） |
| 6 | `gpu_total_mb` | ocr.py::_gpu_total_mb（pynvml）；perfmon.py 自写 NVML ctypes（后者将改为引用本函数） |
| 7 | `load_json` / `save_json` | cache.py::_load / _save 及各脚本零散读写 |

依赖约束：只依赖标准库 + psutil（可选）+ pynvml（可选），两个可选依赖缺失时函数降级不抛异常，
避免在导入期就把 GUI/CLI 拖垮。
"""
import ctypes
import json
import os
from enum import Enum

from .constants import REMOTE_SOFTWARE

__all__ = [
    "jdefault", "jdumps",
    "KEY_MAP", "VK_NAME", "key_name", "vk_of",
    "pids_by_name", "proc_running", "find_pid_by_name", "remote_tools_running",
    "proc_stats", "gpu_total_mb", "load_json", "save_json",
]

# ---------------------------------------------------------------- 1. JSON
def jdefault(o):
    """JSON 序列化兜底：枚举 → value；其余 → str。

    取代 locate.py 与 uitool.py 中两份已漂移的 `_jdefault`。
    """
    if isinstance(o, Enum):
        return o.value
    return str(o)


def jdumps(obj, **kw):
    """项目统一 JSON 输出：ensure_ascii=False + default=jdefault。"""
    kw.setdefault("ensure_ascii", False)
    kw.setdefault("default", jdefault)
    return json.dumps(obj, **kw)


# ---------------------------------------------------------------- 2. 键码
KEY_MAP = {}
for _i in range(1, 25):
    KEY_MAP["F%d" % _i] = 0x6F + _i
KEY_MAP.update({
    "INSERT": 0x2D, "INS": 0x2D, "HOME": 0x24, "PAGEUP": 0x21, "PGUP": 0x21,
    "PAGEDOWN": 0x22, "PGDN": 0x22, "DELETE": 0x2E, "DEL": 0x2E, "END": 0x23,
    "SPACE": 0x20, "ESC": 0x1B, "TAB": 0x09, "ENTER": 0x0D,
    "BACKSPACE": 0x08, "NUMLOCK": 0x90, "SCROLLLOCK": 0x91,
})
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY_MAP[_c] = ord(_c)
for _c in "0123456789":
    KEY_MAP[_c] = ord(_c)
VK_NAME = {v: k for k, v in KEY_MAP.items()}


def key_name(vk):
    """VK → 键名（未知返回 VK<num>）。"""
    return VK_NAME.get(vk, "VK%d" % vk)


def vk_of(name):
    """键名 → VK（支持 'F10' / 'insert' / 'A' / '0x79' / '121'）；未知返回 None。"""
    if name is None:
        return None
    s = str(name).strip()
    if not s:
        return None
    if s.lower().startswith("0x"):
        try:
            return int(s, 16)
        except ValueError:
            return None
    if s.isdigit():
        try:
            return int(s)
        except ValueError:
            return None
    return KEY_MAP.get(s.upper())


# ---------------------------------------------------------------- 3. 进程
def _import_psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def _base(name):
    return os.path.splitext(str(name))[0].lower()


def pids_by_name(name):
    """按 exe 名（去扩展名、小写比对）列出全部匹配 PID。失败返回 []。"""
    psutil = _import_psutil()
    if psutil is None:
        return []
    base = _base(name)
    out = []
    try:
        for p in psutil.process_iter(["name"]):
            try:
                nm = (p.info.get("name") or "").lower()
            except Exception:
                continue
            if nm.split(".")[0] == base:
                out.append(p.pid)
    except Exception:
        pass
    return out


def proc_running(name):
    """目标程序是否在运行：返回首个匹配 PID 或 None（与 testbar.proc_running 同语义）。"""
    pids = pids_by_name(name)
    return pids[0] if pids else None


def find_pid_by_name(name):
    """按 exe 名找 PID；同名多个时取 CPU 时间累计最高（最活跃）的一个，无则返回 None。

    对齐 perfmon.find_pid_by_name 的"取最活跃"语义，底层由 EnumProcesses+PSAPI 改为 psutil。
    """
    psutil = _import_psutil()
    if psutil is None:
        return None
    base = _base(name)
    best_pid, best_cpu = None, -1.0
    try:
        for p in psutil.process_iter(["name"]):
            try:
                nm = (p.info.get("name") or "").lower()
            except Exception:
                continue
            if nm.split(".")[0] != base:
                continue
            try:
                t = p.cpu_times()
                cpu = (t.user or 0.0) + (t.system or 0.0)
            except Exception:
                cpu = 0.0
            if cpu > best_cpu:
                best_cpu, best_pid = cpu, p.pid
    except Exception:
        pass
    return best_pid


def remote_tools_running(names=None):
    """检测正在运行的远程控制软件，返回命中的进程名列表（小写、去重、按名单顺序）。

    names 默认取 core.constants.REMOTE_SOFTWARE（testbar/env_probe 两份名单的并集）。
    """
    psutil = _import_psutil()
    if psutil is None:
        return []
    watch = [str(n).lower() for n in (names if names is not None else REMOTE_SOFTWARE)]
    found, seen = [], set()
    try:
        for p in psutil.process_iter(["name"]):
            try:
                nm = (p.info.get("name") or "").lower()
            except Exception:
                continue
            if not nm:
                continue
            base = nm.split(".")[0]
            if base in watch and base not in seen:
                seen.add(base)
                found.append(base)
    except Exception:
        pass
    return [w for w in watch if w in seen]


# ---------------------------------------------------------------- 4. 进程统计
def proc_stats(pid):
    """进程 CPU 累计毫秒与内存 MB（替代 perfmon 自写的 FILETIME/PSAPI 段）。

    返回 {"pid", "cpu_ms", "mem_mb"}；失败返回 None。
    """
    psutil = _import_psutil()
    if psutil is None:
        return None
    try:
        p = psutil.Process(int(pid))
        t = p.cpu_times()
        mem = p.memory_info().rss / 1024 / 1024
        return {
            "pid": p.pid,
            "cpu_ms": round(((t.user or 0.0) + (t.system or 0.0)) * 1000, 2),
            "mem_mb": round(mem, 2),
        }
    except Exception:
        return None


# ---------------------------------------------------------------- 5. GPU
def gpu_total_mb():
    """显存总量（MiB），走 NVIDIA 官方 pynvml（无进程启动开销）；失败回退 12288。

    来自 ocr.py::_gpu_total_mb，含 Windows 下 nvml.dll 仅存在于 System32 的预加载兼容段。
    """
    try:
        import pynvml
        if getattr(pynvml, "nvmlLib", None) is None:
            cands = [
                os.path.join(os.getenv("ProgramFiles", "C:/Program Files"),
                             "NVIDIA Corporation", "NVSMI", "nvml.dll"),
                "nvml.dll",
            ]
            for cand in cands:
                try:
                    pynvml.nvmlLib = ctypes.CDLL(cand)
                    break
                except OSError:
                    continue
        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return int(info.total / 1024 / 1024)
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return 12288


# ---------------------------------------------------------------- 6. 配置读写
def load_json(path, default=None):
    """读 JSON 文件；不存在或解析失败返回 default（不抛异常）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    """写 JSON 文件（ensure_ascii=False，indent=2）；成功返回 True。"""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=jdefault)
        return True
    except Exception:
        return False
