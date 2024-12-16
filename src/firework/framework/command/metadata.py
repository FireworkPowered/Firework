from __future__ import annotations

from dataclasses import Field, dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable

from elaina_segment import SEPARATORS

from .globals import FRAGMENT_METADATA_IDENT, UNION_METADATA_IDENT, FieldTwin

if TYPE_CHECKING:
    from .core.model.capture import Capture
    from .core.model.fragment import FragmentGroup
    from .core.model.receiver import Rx


@dataclass
class FragmentMetadata:
    variadic: bool = False
    separators: str | None = None
    group: FragmentGroup | None = None
    hybrid_separators: bool = True

    owned_option: OptionMetadata | None = None
    is_header: bool = False

    capture: Capture | None = None
    receiver: Rx[Any] | None = None
    validator: Callable[[Any], bool] | None = None
    transformer: Callable[[Any], Any] | None = None

    @staticmethod
    def get(dc_field: Field):
        if FRAGMENT_METADATA_IDENT not in dc_field.metadata:
            raise AttributeError("Fragment metadata is not found")

        return dc_field.metadata[FRAGMENT_METADATA_IDENT]

    @classmethod
    def build_default(cls):
        return cls()

    @staticmethod
    def get_or_default(dc_field: Field):
        if FRAGMENT_METADATA_IDENT not in dc_field.metadata:
            return FragmentMetadata.build_default()

        return dc_field.metadata[FRAGMENT_METADATA_IDENT]


@dataclass
class UnionMetadata:
    twins: list[FieldTwin]

    @staticmethod
    def get(dc_field: Field) -> UnionMetadata | None:
        if UNION_METADATA_IDENT not in dc_field.metadata:
            return

        return dc_field.metadata[UNION_METADATA_IDENT]

    @staticmethod
    def get_strict(dc_field: Field) -> UnionMetadata:
        if UNION_METADATA_IDENT not in dc_field.metadata:
            raise AttributeError("Union metadata is not found")

        return dc_field.metadata[UNION_METADATA_IDENT]


@dataclass
class SubcommandMetadata:
    keyword: str
    aliases: Iterable[str] = ()
    prefixes: Iterable[str] = ()
    separators: str = SEPARATORS

    soft_keyword: bool = False
    compact_header: bool = False
    enter_instantly: bool = False


@dataclass
class OptionMetadata:
    keyword: str
    aliases: list[str] = field(default_factory=list)
    separators: str = SEPARATORS
    header_separators: str | None = None

    soft_keyword: bool = False
    compact_header: bool = False
    allow_duplicate: bool = False
    forwarding: bool = True
    hybrid_separators: bool = False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self is other
        return NotImplemented

    def __hash__(self):
        return id(self)
