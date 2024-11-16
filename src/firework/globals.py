from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bootstrap import Bootstrap
    from .config import ConfigManager


BOOTSTRAP_CONTEXT: ContextVar[Bootstrap] = ContextVar("BOOTSTRAP_CONTEXT")
CONFIG_MANAGER_CONTEXT: ContextVar[ConfigManager] = ContextVar("CONFIG_MANAGER_CONTEXT")
