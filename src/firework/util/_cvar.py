from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

T = TypeVar("T")


@contextmanager
def cvar(ctx: ContextVar[T], val: T):
    token = ctx.set(val)
    try:
        yield val
    finally:
        ctx.reset(token)
