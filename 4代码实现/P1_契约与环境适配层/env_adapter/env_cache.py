# -*- coding: utf-8 -*-
"""env_adapter/env_cache.py — 环境探测结果缓存（TTL + 失效 + 版本）。"""
import time

from contracts import EnvProfile


class EnvCache:
    def __init__(self, ttl_s: float = 30.0):
        self._ttl = ttl_s
        self._d = {}

    def get(self, key: str, now: float | None = None) -> EnvProfile | None:
        """命中且未过期返回 EnvProfile；否则 None（过期即失效，不返回脏数据）。"""
        now = now or time.time()
        item = self._d.get(key)
        if not item:
            return None
        prof, ts, version = item
        if now - ts > self._ttl:
            self._d.pop(key, None)
            return None
        if version != prof.version:
            self._d.pop(key, None)
            return None
        return prof

    def put(self, key: str, prof: EnvProfile, now: float | None = None) -> None:
        self._d[key] = (prof, now or time.time(), prof.version)

    def invalidate(self, key: str, condition: str | None = None) -> bool:
        """失效单个 key。condition 用于审计记录失效原因。"""
        return self._d.pop(key, None) is not None

    def clear(self) -> None:
        self._d.clear()

    def keys(self) -> list:
        return list(self._d.keys())
