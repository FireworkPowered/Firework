from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from firework.util import cvar

from .entity import BaseEntity
from .globals import COLLECTING_IMPLEMENT_ENTITY, COLLECTING_TARGET_RECORD
from .record import EntrypointRecord

if TYPE_CHECKING:
    from .context import CollectContext
    from .entrypoint import CollectEndpointTarget, Entrypoint


class EntrypointImplement(BaseEntity):
    targets: list[tuple[Entrypoint, CollectEndpointTarget]]
    impl: Callable

    def __init__(self, impl: Callable):
        self.targets = []
        self.impl = impl

    def add_target(self, endpoint: Entrypoint, generator: CollectEndpointTarget):
        self.targets.append((endpoint, generator))

    def collect(self, collector: CollectContext):
        super().collect(collector)

        with cvar(COLLECTING_IMPLEMENT_ENTITY, self):
            for endpoint, generator in self.targets:
                record_signature = endpoint.signature

                if record_signature in collector.fn_implements:
                    record = collector.fn_implements[record_signature]
                else:
                    record = collector.fn_implements[record_signature] = EntrypointRecord()

                with cvar(COLLECTING_TARGET_RECORD, record):
                    for signal in generator:
                        signal.overload.lay(record, signal.value, self.impl)

        return self

    @staticmethod
    def current():
        return COLLECTING_IMPLEMENT_ENTITY.get()
