# -*- coding: utf-8 -*-
"""perfmon.py — Windows 进程性能采样（CPU/内存/GPU/显存），供 testbar 实时绘图。

- 进程 CPU%：GetProcessTimes 差值 / 墙钟（与任务管理器口径一致）
- 进程内存：GetProcessMemoryInfo.WorkingSetSize
- GPU：NVML（nvml.dll，nvidia-smi 的底层原生库）ctypes 直调——
      整卡利用率 + 显存 + 按进程显存，全程无外部进程、无窗口
- 目标进程查找：EnumProcesses + GetModuleBaseNameW 原生枚举，不拉 PowerShell
- 环形缓冲：默认 90 点，1 秒采样一次

用法：
  import perfmon
  pm = perfmon.PerfMonitor(interval=1.0, points=90)
  pm.set_target(pid)            # 或 set_target_by_name("cookie_sync.exe")
  pm.start()
  ... time.sleep(3) ...
  print(pm.snapshot())          # {'console': {...}, 'target': {...}}
  pm.stop()
"""
import ctypes
import os
import threading
import time
from collections import deque
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD)]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


# 统一 64 位句柄签名，防止截断
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                 wintypes.DWORD]
kernel32.GetProcessTimes.restype = wintypes.BOOL
kernel32.GetProcessTimes.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
psapi.GetProcessMemoryInfo.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
    wintypes.DWORD]
psapi.EnumProcesses.restype = wintypes.BOOL
psapi.EnumProcesses.argtypes = [ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD)]
psapi.GetModuleBaseNameW.restype = wintypes.DWORD
psapi.GetModuleBaseNameW.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]


def _ft_ms(ft):
    return (ft.dwHighDateTime << 32 | ft.dwLowDateTime) / 10000.0


def process_times(pid):
    """返回 (kernel_ms, user_ms) 累计 CPU 时间。失败返回 None。"""
    h = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        k, u, c, e = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e),
                                        ctypes.byref(k), ctypes.byref(u)):
            return None
        return _ft_ms(k), _ft_ms(u)
    finally:
        kernel32.CloseHandle(h)


def process_memory_mb(pid):
    """进程工作集内存 MB。失败返回 None。"""
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if not psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            return None
        return pmc.WorkingSetSize / (1024 * 1024)
    finally:
        kernel32.CloseHandle(h)


# ---------- NVML：原生 GPU 采样（替代 nvidia-smi 外部进程） ----------
# nvidia-smi 底层就是 nvml.dll；ctypes 直调可拿到同样的
# 整卡利用率/显存 + 按进程显存，且不启动任何外部程序（无窗口闪现）。
class _NvmlUtil(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class _NvmlMem(ctypes.Structure):
    _fields_ = [("total", ctypes.c_ulonglong),
                ("free", ctypes.c_ulonglong),
                ("used", ctypes.c_ulonglong)]


class _NvmlProcV2(ctypes.Structure):      # nvmlProcessInfo_t v2
    _fields_ = [("pid", ctypes.c_uint),
                ("usedGpuMemory", ctypes.c_ulonglong)]


class _NvmlProcV3(ctypes.Structure):      # nvmlProcessInfo_t v3
    _fields_ = [("pid", ctypes.c_uint),
                ("usedGpuMemory", ctypes.c_ulonglong),
                ("gpuInstanceId", ctypes.c_uint),
                ("computeInstanceId", ctypes.c_uint)]


class NVML:
    """nvml.dll 原生封装。惰性加载；失败时 gpu_info 返回 None，不抛异常。"""
    _lib = None
    _handle = None
    _tried = False

    @classmethod
    def _load(cls):
        if cls._tried:
            return cls._lib is not None
        cls._tried = True
        candidates = [
            "C:\\Windows\\System32\\nvml.dll",   # NVIDIA 驱动安装位置
            "nvml.dll",
        ]
        lib = None
        for p in candidates:
            try:
                lib = ctypes.WinDLL(p)
                break
            except OSError:
                continue
        if lib is None:
            return False
        try:
            lib.nvmlInit_v2()
            h = ctypes.c_void_p()
            lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(h))
            cls._lib = lib
            cls._handle = h
            return True
        except Exception:
            return False

    @staticmethod
    def card():
        """整卡 {util, mem_used_mb, mem_total_mb}；失败返回 None。"""
        if not NVML._load():
            return None
        try:
            u = _NvmlUtil()
            NVML._lib.nvmlDeviceGetUtilizationRates(NVML._handle,
                                                    ctypes.byref(u))
            m = _NvmlMem()
            NVML._lib.nvmlDeviceGetMemoryInfo(NVML._handle, ctypes.byref(m))
            return {"util": float(u.gpu),
                    "mem_used_mb": m.used / 1048576.0,
                    "mem_total_mb": m.total / 1048576.0}
        except Exception:
            return None

    @staticmethod
    def per_pid():
        """{pid: 显存MB}（compute+graphics 进程合并）；失败返回 {}。
        实测本机（RTX 4080 Laptop + 当前驱动）nvmlProcessInfo_t 为 24 字节：
        pid@0 / usedGpuMemory@8（nvml-smi --query-compute-apps 22/22 匹配）。
        缓冲按 128B/元素裕量分配，防新驱动结构体扩展后越界写；
        显存 N/A 时 NVML 返回 0xFFFFFFFFFFFFFFFF，与 nvidia-smi 的 [N/A] 一致，
        此时该进程不进入结果（整卡显存不受影响）。"""
        if not NVML._load():
            return {}
        out = {}
        try:
            for fn in ("nvmlDeviceGetComputeRunningProcesses_v3",
                       "nvmlDeviceGetGraphicsRunningProcesses_v3",
                       "nvmlDeviceGetComputeRunningProcesses_v2",
                       "nvmlDeviceGetGraphicsRunningProcesses_v2"):
                f = getattr(NVML._lib, fn, None)
                if f is None:
                    continue
                cnt = ctypes.c_uint(0)
                f(NVML._handle, ctypes.byref(cnt), None)
                n = cnt.value
                if n <= 0 or n > 4096:
                    continue
                buf = (ctypes.c_ubyte * (n * 128))()
                cnt2 = ctypes.c_uint(n)
                if f(NVML._handle, ctypes.byref(cnt2), buf) != 0:
                    continue
                for i in range(cnt2.value):
                    off = i * 24                     # nvmlProcessInfo_t 步长
                    pid = int.from_bytes(bytes(buf[off:off + 4]), "little")
                    if pid == 0 or pid == 0xFFFFFFFF:   # 无效/已退出哨兵
                        continue
                    used = int.from_bytes(bytes(buf[off + 8:off + 16]),
                                          "little")
                    if used and used != 0xFFFFFFFFFFFFFFFF:
                        out[pid] = used / 1048576.0
        except Exception:
            pass
        return out


def gpu_info():
    """整卡 GPU：{util, mem_used_mb, mem_total_mb, per_pid:{pid:mb}}。"""
    card = NVML.card()
    per = NVML.per_pid()
    if card is None:
        return {"util": None, "mem_used_mb": None, "mem_total_mb": None,
                "per_pid": per}
    out = dict(card)
    out["per_pid"] = per
    return out


def find_pid_by_name(name):
    """EnumProcesses + GetModuleBaseNameW 原生枚举，按 exe 名匹配同名进程。
    同名多个时取 CPU 时间累计最高（最近活跃）的一个；返回 PID 或 None。
    全程不启动外部程序（无窗口闪现）。"""
    base = os.path.splitext(name)[0].lower()
    best_pid = None
    best_times = -1.0
    pids = (wintypes.DWORD * 16384)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(pids), ctypes.sizeof(pids),
                               ctypes.byref(needed)):
        return None
    n = needed.value // 4
    for i in range(n):
        pid = pids[i]
        if not pid:
            continue
        # QUERY_LIMITED | QUERY_INFORMATION | VM_READ —— GetModuleBaseNameW 需要
        h = kernel32.OpenProcess(0x1000 | 0x0400 | 0x0010, False, pid)
        if not h:
            continue
        try:
            buf = ctypes.create_unicode_buffer(260)
            size = psapi.GetModuleBaseNameW(h, None,
                                            ctypes.cast(buf, ctypes.c_void_p),
                                            260)
            if size and buf.value.lower().split(".")[0] == base:
                t = process_times(pid)
                score = (t[0] + t[1]) if t else 0.0
                if score >= best_times:
                    best_times = score
                    best_pid = pid
        finally:
            kernel32.CloseHandle(h)
    return best_pid


class PerfMonitor(threading.Thread):
    """每秒采样两个对象：console(本进程) 与 target(目标进程)。

    snapshot() 返回：
      {'console': {'cpu': [...], 'mem': [...], 'gpu': [...], 'vram': [...]},
       'target': 同上,
       'gpu_card': {'util': 最新, 'mem_used_mb': 最新, 'mem_total_mb': 最新},
       'target_ok': bool, 'target_name': str}
    每个序列为环形缓冲 deque（长度 points），None 表示该点无效。
    """

    def __init__(self, interval=1.0, points=90):
        super().__init__(daemon=True)
        self.interval = interval
        self.points = points
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.console_pid = os.getpid()
        self.target_pid = None
        self.target_name = ""
        self._t0_console = time.time()   # 审计：console/target 各自独立计时基点
        self._t0_target = None
        self._console_times = process_times(self.console_pid)
        self._target_times = None
        self._data = {"console": self._blank(), "target": self._blank()}
        self._gpu_card = {"util": None, "mem_used_mb": None,
                          "mem_total_mb": None}
        self._gpu_t0 = 0
        self._gpu_cache = {}

    def _blank(self):
        return {"cpu": deque([None] * self.points, maxlen=self.points),
                "mem": deque([None] * self.points, maxlen=self.points),
                "gpu": deque([None] * self.points, maxlen=self.points),
                "vram": deque([None] * self.points, maxlen=self.points)}

    def set_target(self, pid, name=""):
        with self._lock:
            self.target_pid = pid
            self.target_name = name or str(pid)
            self._target_times = process_times(pid)
            self._data["target"] = self._blank()
            self._data["console"] = self._blank()

    def set_target_by_name(self, name):
        """按 exe 文件名匹配进程（原生枚举，不启动外部程序）。"""
        pid = find_pid_by_name(name)
        if pid is None:
            return False
        self.set_target(pid, os.path.splitext(name)[0] + ".exe")
        return True

    def run(self):
        err_count = 0
        while not self._stop.is_set():
            try:
                self._sample()
                err_count = 0
            except Exception as e:
                err_count += 1
                # 审计：异常不再静默吞掉，最多每 30 次打印一条防刷屏
                if err_count == 1 or err_count % 30 == 0:
                    import sys
                    print("[perfmon] 采样异常 x%d: %s" % (err_count, e),
                          file=sys.stderr)
            self._stop.wait(self.interval)

    def _sample(self):
        now = time.time()
        gpu = gpu_info()
        self._gpu_cache = gpu
        if gpu["util"] is not None:
            self._gpu_card = {"util": gpu["util"],
                              "mem_used_mb": gpu["mem_used_mb"],
                              "mem_total_mb": gpu["mem_total_mb"]}
        with self._lock:
            self._push("console", now, gpu)
            if self.target_pid:
                self._push("target", now, gpu)

    def _push(self, key, now, gpu):
        d = self._data[key]
        pid = self.console_pid if key == "console" else self.target_pid
        times = process_times(pid)
        mem = process_memory_mb(pid)
        d["cpu"].append(self._cpu_pct(times, key, now))
        d["mem"].append(mem)
        vram = gpu["per_pid"].get(pid)
        d["gpu"].append(gpu["util"] if pid else None)
        d["vram"].append(vram)

    def _cpu_pct(self, times, key, now):
        if not times:
            return None
        prev = self._console_times if key == "console" else self._target_times
        if not prev:
            self._set_prev(key, times, now)
            return None
        k0, u0 = prev
        k1, u1 = times
        dt = now - (self._t0_console if key == "console" else self._t0_target)
        if dt <= 0:
            return 0.0  # 同一采样时刻无消耗 = 0%（审计：console/target 各自计时）
        pct = ((k1 - k0) + (u1 - u0)) / 1000.0 / dt * 100.0
        self._set_prev(key, times, now)
        return max(0.0, min(100.0, pct))

    def _set_prev(self, key, times, now):
        if key == "console":
            self._console_times = times
            self._t0_console = now
        else:
            self._target_times = times
            self._t0_target = now

    def snapshot(self):
        with self._lock:
            out = {"console": {k: list(v) for k, v in
                               self._data["console"].items()},
                   "target": {k: list(v) for k, v in
                              self._data["target"].items()},
                   "gpu_card": dict(self._gpu_card),
                   "target_ok": self.target_pid is not None,
                   "target_name": self.target_name}
            return out

    def stop(self):
        self._stop.set()


if __name__ == "__main__":
    import sys
    pm = PerfMonitor(interval=0.5, points=10)
    pm.set_target_by_name(sys.argv[1] if len(sys.argv) > 1 else "explorer")
    pm.start()
    time.sleep(2.5)
    s = pm.snapshot()
    print("target:", s["target_name"], "ok:", s["target_ok"])
    print("console cpu 最新:", s["console"]["cpu"][-1],
          "mem:", s["console"]["mem"][-1])
    print("target  cpu 最新:", s["target"]["cpu"][-1],
          "mem:", s["target"]["mem"][-1])
    print("gpu_card:", s["gpu_card"])
    pm.stop()
