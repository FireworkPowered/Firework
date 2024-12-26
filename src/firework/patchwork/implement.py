from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from firework.util import cvar

from .entity import BaseEntity
from .globals import COLLECTING_IMPLEMENT_ENTITY, COLLECTING_TARGET_RECORD
from .record import FeatureRecord

if TYPE_CHECKING:
    from .context import CollectContext
    from .feature import CollectEndpointTarget, Feature


class EntrypointImplement(BaseEntity):
    targets: list[tuple[Feature, CollectEndpointTarget]]
    impl: Callable

    def __init__(self, impl: Callable):
        self.targets = []
        self.impl = impl

    def add_target(self, endpoint: Feature, generator: CollectEndpointTarget):
        self.targets.append((endpoint, generator))

    def collect(self, collector: CollectContext):
        super().collect(collector)

        with cvar(COLLECTING_IMPLEMENT_ENTITY, self):
            for endpoint, generator in self.targets:
                record_signature = endpoint.signature

                if record_signature in collector.fn_implements:
                    record = collector.fn_implements[record_signature]
                else:
                    record = collector.fn_implements[record_signature] = FeatureRecord()

                with cvar(COLLECTING_TARGET_RECORD, record):
                    for signal in generator:
                        signal.overload.lay(record, signal.value, self.impl)

        return self

    @staticmethod
    def current():
        return COLLECTING_IMPLEMENT_ENTITY.get()
