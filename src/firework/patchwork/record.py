from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .feature import Feature
    from .overload import OverloadSpec


@dataclass(eq=True, frozen=True)
class EntrypointRecordLabel:
    endpoint: Feature


@dataclass(eq=True, frozen=True)
class FeatureRecord:
    scopes: dict[str, dict[Any, Any]] = field(default_factory=dict)
    entities: dict[frozenset[tuple[str, OverloadSpec, Any]], Callable] = field(default_factory=dict)


@dataclass(eq=True, frozen=True)
class CollectSignal:
    overload: OverloadSpec
    value: Any
