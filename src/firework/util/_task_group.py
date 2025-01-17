from __future__ import annotations

import asyncio
from typing import Coroutine, Iterable


class TaskGroup:
    tasks: list[asyncio.Task]
    main: asyncio.Task | None = None
    _stop: bool = False
    _notify: asyncio.Event

    def __init__(self):
        self.tasks = []
        self._notify = asyncio.Event()

    def flush(self):
        if self.main is not None:
            self._notify.set()

    def stop(self):
        self._stop = True
        self.flush()

    def spawn(self, task: asyncio.Task | Coroutine):
        task = asyncio.create_task(task) if asyncio.iscoroutine(task) else task
        self.tasks.append(task)

        self.flush()
        return task

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
            if not self.tasks:
                await self._notify.wait()
                self._notify.clear()

            self.main = asyncio.create_task(asyncio.wait(self.tasks))
            awaiting_notify = asyncio.create_task(self._notify.wait())

            await asyncio.wait([self.main, awaiting_notify], return_when=asyncio.FIRST_COMPLETED)

            if awaiting_notify.done():
                self._notify.clear()
                if self._stop:
                    break

                continue

            await self.main
            return

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        await self.wait()

    def __await__(self):
        return self.wait().__await__()
