from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from .context import CollectContext

if TYPE_CHECKING:
    from .feature import Feature
    from .implement import FeatureImpl
    from .record import FeatureRecord
    from .typing import TEntity


GLOBAL_COLLECT_CONTEXT = CollectContext()
COLLECTING_CONTEXT_VAR = ContextVar("CollectingContext", default=GLOBAL_COLLECT_CONTEXT)

COLLECTING_IMPLEMENT_ENTITY: ContextVar[FeatureImpl] = ContextVar("CollectingImplementEntity")
COLLECTING_TARGET_RECORD: ContextVar[FeatureRecord] = ContextVar("CollectingTargetRecord")

LOOKUP_LAYOUT_VAR = ContextVar["tuple[CollectContext, ...]"]("LookupContext", default=(GLOBAL_COLLECT_CONTEXT,))

GLOBAL_LOOKUP_DEPTH = {}
LOOKUP_DEPTH: ContextVar[dict[Feature, int]] = ContextVar("CallerTokens", default=GLOBAL_LOOKUP_DEPTH)


def iter_layout(endpoint: Feature):
    index = LOOKUP_DEPTH.get().get(endpoint, -1)
    contexts = LOOKUP_LAYOUT_VAR.get()

    yield from contexts[index + 1 :]


def global_collect(entity: TEntity) -> TEntity:
    return GLOBAL_COLLECT_CONTEXT.collect(entity)


def local_collect(entity: TEntity) -> TEntity:
    return COLLECTING_CONTEXT_VAR.get().collect(entity)


@contextmanager
def union_scope(*contexts: CollectContext):
    token = LOOKUP_LAYOUT_VAR.set((*contexts, *LOOKUP_LAYOUT_VAR.get()))

    try:
        yield
    finally:
        LOOKUP_LAYOUT_VAR.reset(token)
