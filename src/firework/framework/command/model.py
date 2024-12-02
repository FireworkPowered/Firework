from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FragmentMetadata:
    variadic: bool = False
    separators: str | None = None
    hybrid_separators: bool = True
    option: OptionMetadata | None = None

    # TODO: 4-elements


@dataclass
class OptionMetadata: ...


class YanagiCommand: ...
