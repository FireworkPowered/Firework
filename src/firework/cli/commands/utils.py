from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from ..exceptions import LumaConfigError

if TYPE_CHECKING:
    from ..config import LumaConfig
    from ..core import Core

_T = TypeVar("_T")


def ensure_config(meth: Callable[[_T, Core, LumaConfig, Any], Any]) -> Callable[[_T, Core, Any], Any]:
    @functools.wraps(meth)
    def wrapper(self: _T, core: Core, namespace: Any) -> Any:
        if core.config is None:
            raise LumaConfigError("This command requires valid `luma.toml`")
        return meth(self, core, core.config, namespace)

    return wrapper
