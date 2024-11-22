from __future__ import annotations

import asyncio
from typing import Coroutine, Iterable


class TaskGroup:
    tasks: list[asyncio.Task]
    main: asyncio.Task | None = None
    _stop: bool = False

    def __init__(self):
        self.tasks = []

    def flush(self):
        if self.main is not None:
            self.main.cancel()

    def stop(self):
        self._stop = True
        self.flush()

    def update(self, tasks: Iterable[asyncio.Task | Coroutine]):
        tasks = [asyncio.create_task(task) if asyncio.iscoroutine(task) else task for task in tasks]
        self.tasks.extend(tasks)

        self.flush()
        return tasks

    def drop(self, tasks: Iterable[asyncio.Task]):
        for task in tasks:
            self.tasks.remove(task)

        self.flush()

    async def wait(self):
        while True:
            self.main = asyncio.create_task(asyncio.wait(self.tasks))
            try:
                return await self.main
            except asyncio.CancelledError:
                if self._stop:
                    return
