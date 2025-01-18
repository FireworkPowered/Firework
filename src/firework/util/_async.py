from __future__ import annotations

import asyncio
from typing import Coroutine, Iterable

_CoroutineLike = Coroutine | asyncio.Task


def into_tasks(awaitables: Iterable[_CoroutineLike]) -> list[asyncio.Task]:
    return [i if isinstance(i, asyncio.Task) else asyncio.create_task(i) for i in awaitables]


async def unity(
    tasks: Iterable[_CoroutineLike],
    *,
    timeout: float | None = None,  # noqa: ASYNC109
    return_when: str = asyncio.ALL_COMPLETED,
):
    return await asyncio.wait(into_tasks(tasks), timeout=timeout, return_when=return_when)


async def any_completed(tasks: Iterable[_CoroutineLike]):
    done, pending = await unity(tasks, return_when=asyncio.FIRST_COMPLETED)
    return next(iter(done)), pending


async def oneof(*tasks: _CoroutineLike):
    return await any_completed(tasks)
