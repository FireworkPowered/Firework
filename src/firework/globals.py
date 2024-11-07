from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bootstrap import Bootstrap


BOOTSTRAP_CONTEXT: ContextVar[Bootstrap] = ContextVar("BOOTSTRAP_CONTEXT")
