from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from firework.util import cvar

from .typing import TEntity

if TYPE_CHECKING:
    from .fn.record import FnRecord, FnRecordLabel


class CollectContext:
    fn_implements: dict[FnRecordLabel, FnRecord]

    def __init__(self):
        self.fn_implements = {}

    def collect(self, entity: TEntity) -> TEntity:
        entity.collect_context = self
        entity.collect(self)

        return entity

    @contextmanager
    def collect_scope(self):
        from .globals import COLLECTING_CONTEXT_VAR

        with cvar(COLLECTING_CONTEXT_VAR, self):
            yield self

    @contextmanager
    def lookup_scope(self):
        from .globals import LOOKUP_LAYOUT_VAR

        with cvar(LOOKUP_LAYOUT_VAR, (self, *LOOKUP_LAYOUT_VAR.get())):
            yield self

    @contextmanager
    def scope(self):
        with self.collect_scope(), self.lookup_scope():
            yield self
