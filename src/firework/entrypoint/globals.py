from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Tuple

from .context import CollectContext

if TYPE_CHECKING:
    from .entrypoint import Entrypoint
    from .implement import EntrypointImplement
    from .record import EntrypointRecord
    from .typing import TEntity


GLOBAL_COLLECT_CONTEXT = CollectContext()
COLLECTING_CONTEXT_VAR = ContextVar("CollectingContext", default=GLOBAL_COLLECT_CONTEXT)

COLLECTING_IMPLEMENT_ENTITY: ContextVar[EntrypointImplement] = ContextVar("CollectingImplementEntity")
COLLECTING_TARGET_RECORD: ContextVar[EntrypointRecord] = ContextVar("CollectingTargetRecord")

LOOKUP_LAYOUT_VAR = ContextVar[Tuple[CollectContext, ...]]("LookupContext", default=(GLOBAL_COLLECT_CONTEXT,))

LOOKUP_DEPTH: ContextVar[dict[Entrypoint, int]] = ContextVar("CallerTokens", default={})


def iter_layout(endpoint: Entrypoint):
    index = LOOKUP_DEPTH.get().get(endpoint, -1)
    contexts = LOOKUP_LAYOUT_VAR.get()

    for layer in contexts[index + 1 :]:
        yield layer


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
