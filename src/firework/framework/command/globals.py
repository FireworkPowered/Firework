from __future__ import annotations

from collections import ChainMap
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from dataclasses import Field

    from .core.model.fragment import FragmentGroup
    from .core.model.pattern import OptionPattern, SubcommandPattern
    from .metadata import FragmentMetadata, OptionMetadata

FRAGMENT_METADATA_IDENT = "yanagi_fragment"
UNION_METADATA_IDENT = "yanagi_union"

FieldTwin: TypeAlias = "tuple[Field[Any], FragmentMetadata]"

GLBOAL_SUBCOMMANDS: ChainMap[str, SubcommandPattern] = ChainMap()
GLOBAL_OPTIONS_BIND: ChainMap[str, OptionPattern] = ChainMap()

YANAGI_CURRENT_OPTION: ContextVar[OptionMetadata | None] = ContextVar("YANAGI_CURRENT_OPTION", default=None)
YANAGI_CURRENT_FRAGMENT_GROUP: ContextVar[FragmentGroup | None] = ContextVar("YANAGI_CURRENT_FRAGMENT_GROUP", default=None)
YANAGI_INHERITED_SUBCOMMANDS: ContextVar[ChainMap[str, SubcommandPattern] | None] = ContextVar(
    "YANAGI_INHERITED_SUBCOMMANDS", default=None
)
YANAGI_INHERITED_OPTIONS: ContextVar[ChainMap[str, OptionPattern] | None] = ContextVar("YANAGI_INHERITED_OPTIONS", default=None)
