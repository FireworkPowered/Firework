from __future__ import annotations

import asyncio
from heapq import heappop, heappush
from time import time
from typing import TYPE_CHECKING, Any

from firework.bootstrap import Service, ServiceContext

if TYPE_CHECKING:
    from datetime import timedelta


class Memcache:
    cache: dict[str, tuple[float | None, Any]]
    expire: list[tuple[float, str]]

    def __init__(
        self,
        cache: dict[str, tuple[float | None, Any]],
        expire: list[tuple[float, str]],
    ):
        self.cache = cache
        self.expire = expire

    async def get(self, key: str, default: Any = None) -> Any:
        value = self.cache.get(key)
        if value:
            if value[0] is None or value[0] >= time():
                return value[1]
            del self.cache[key]
        return default

    async def set(self, key: str, value: Any, expire: timedelta | None = None) -> None:
        if expire is None:
            self.cache[key] = (None, value)
        else:
            expire_time = time() + expire.total_seconds()
            self.cache[key] = (expire_time, value)
            heappush(self.expire, (expire_time, key))

    async def delete(self, key: str, *, strict: bool = False) -> None:
        if strict or key in self.cache:
            del self.cache[key]

    async def clear(self) -> None:
        self.cache.clear()
        self.expire.clear()

    async def has(self, key: str) -> bool:
        return key in self.cache

    async def keys(self) -> list[str]:
        return list(self.cache.keys())


class MemcacheService(Service):
    id = "memcache"

    interval: float
    _cache: dict[str, tuple[float | None, Any]]
    expire: list[tuple[float, str]]

    def __init__(
        self,
        interval: float = 0.1,
        cache: dict[str, tuple[float | None, Any]] | None = None,
        expire: list[tuple[float, str]] | None = None,
    ):
        self.interval = interval
        self._cache = cache or {}
        self.expire = expire or []

    @property
    def cache(self):
        return Memcache(self._cache, self.expire)

    async def launch(self, context: ServiceContext) -> None:
        async with context.prepare():
            pass

        if context.ready:
            while not context.should_exit:
                while self.expire and self.expire[0][0] <= time():
                    _, key = heappop(self.expire)
                    self._cache.pop(key, None)
                await asyncio.sleep(self.interval)

        async with context.cleanup():
            pass
