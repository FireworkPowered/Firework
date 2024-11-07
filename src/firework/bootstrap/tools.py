from __future__ import annotations

from typing import AsyncContextManager, Callable, Generic, TypeVar

from firework.bootstrap import Service, ServiceContext

T = TypeVar("T")


class LifespanHelper(Generic[T], Service):
    _value: T

    def __init__(self, id: str, handler: Callable[[], AsyncContextManager[T]]):
        self.id = id
        self.handler = handler

    @classmethod
    def create(cls, id: str):
        def decorator(handler: Callable[[], AsyncContextManager[T]]):
            return cls(id, handler)

        return decorator

    async def launch(self, context: ServiceContext):
        target = self.handler()

        async with context.prepare():
            self._value = await target.__aenter__()

        async with context.online():
            pass

        async with context.cleanup():
            await target.__aexit__(None, None, None)
