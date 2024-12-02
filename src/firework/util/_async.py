from __future__ import annotations

import asyncio
from typing import Coroutine, Iterable

from loguru import logger

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


def cancel_alive_tasks(loop: asyncio.AbstractEventLoop):
    to_cancel = asyncio.tasks.all_tasks(loop)
    if to_cancel:
        for tsk in to_cancel:
            tsk.cancel()
        loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

        for task in to_cancel:  # pragma: no cover
            # BELIEVE IN PSF
            if task.cancelled():
                continue
            if task.exception() is not None:
                logger.opt(exception=task.exception()).error(f"Unhandled exception when shutting down {task}:")
