from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from contextvars import ContextVar

T = TypeVar("T")


@contextmanager
def cvar(ctx: ContextVar[T], val: T):
    token = ctx.set(val)
    try:
        yield val
    finally:
        ctx.reset(token)
