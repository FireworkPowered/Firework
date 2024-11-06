from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import CollectContext


class BaseEntity:
    collect_context: CollectContext | None = None

    def collect(self, collector: CollectContext):
        ...
