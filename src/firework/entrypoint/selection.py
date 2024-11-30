from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterator

from .globals import LOOKUP_DEPTH, iter_layout
from .typing import C, P, R

if TYPE_CHECKING:
    from .entrypoint import Entrypoint
    from .overload import OverloadSpec, TCallValue
    from .record import EntrypointRecord


@dataclass
class Candidates(Generic[C]):
    endpoint: Entrypoint
    expect_complete: bool = False

    def __iter__(self) -> Iterator[Selection[C]]:
        sig = self.endpoint.signature

        last_selection = None
        try:
            for layer in iter_layout(self.endpoint):
                if sig in layer.fn_implements:
                    last_selection = Selection(layer.fn_implements[sig], self.endpoint)
                    yield last_selection
                    if last_selection.completed:
                        break
        finally:
            if self.expect_complete and (last_selection is None or not last_selection.completed):
                raise NotImplementedError("cannot lookup any implementation with given arguments")


@dataclass
class Selection(Generic[C]):
    record: EntrypointRecord
    endpoint: Entrypoint
    result: dict[C, None] | None = None
    completed: bool = False

    def accept(self, collection: dict[Callable, None]):
        if self.result is None:
            self.result = collection  # type: ignore
        else:
            self.result = dict(self.result.items() & collection.items())

    def harvest(self, overload: OverloadSpec[Any, Any, TCallValue], value: TCallValue):
        digs = overload.dig(self.record, value)
        self.accept(digs)
        return digs

    def complete(self):
        self.completed = True

    def _wraps(self, raw: C) -> C:
        @functools.wraps(raw)
        def wrapper(*args, **kwargs):
            tokens = LOOKUP_DEPTH.get()
            current_index = tokens.get(self.endpoint, -1)
            _tok = LOOKUP_DEPTH.set({**tokens, self.endpoint: current_index + 1})

            try:
                return raw(*args, **kwargs)
            finally:
                LOOKUP_DEPTH.reset(_tok)

        return wrapper  # type: ignore

    def __iter__(self):
        if self.result is None:
            raise NotImplementedError("cannot lookup any implementation with given arguments")

        for raw in self.result:
            yield self._wraps(raw)

    def __call__(self: Selection[Callable[P, R]], *args: P.args, **kwargs: P.kwargs) -> R:
        for i in self:
            return i(*args, **kwargs)

        raise NotImplementedError("cannot lookup any implementation with given arguments")

    def __bool__(self):
        return bool(self.result)
