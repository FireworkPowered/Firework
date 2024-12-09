from __future__ import annotations

from dataclasses import MISSING
from typing import Any, Callable

from elaina_segment import SEPARATORS

from .core.model.receiver import AddRx, CountRx
from .model import fragment, header_fragment, option


def constant_option(
    keyword: str,
    value: Any,
    default: Any = MISSING,
    default_factory: Callable[[], Any] = MISSING,  # type: ignore
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = None,
    *,
    soft_keyword: bool = False,
    compact_header: bool = False,
    allow_duplicate: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = False,
):
    with option(
        keyword,
        aliases,
        separators,
        header_separators,
        soft_keyword=soft_keyword,
        compact_header=compact_header,
        allow_duplicate=allow_duplicate,
        forwarding=forwarding,
        hybrid_separators=hybrid_separators,
    ):
        return header_fragment(default=default, default_factory=default_factory, transformer=lambda _: value)


def truthy_option(
    keyword: str,
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = None,
    *,
    soft_keyword: bool = False,
    compact_header: bool = False,
    allow_duplicate: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = False,
):
    return constant_option(
        keyword=keyword,
        value=True,
        default=False,
        aliases=aliases,
        separators=separators,
        header_separators=header_separators,
        soft_keyword=soft_keyword,
        compact_header=compact_header,
        allow_duplicate=allow_duplicate,
        forwarding=forwarding,
        hybrid_separators=hybrid_separators,
    )


def falsy_option(
    keyword: str,
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = None,
    *,
    soft_keyword: bool = False,
    compact_header: bool = False,
    allow_duplicate: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = False,
):
    return constant_option(
        keyword=keyword,
        value=False,
        default=True,
        aliases=aliases,
        separators=separators,
        header_separators=header_separators,
        soft_keyword=soft_keyword,
        compact_header=compact_header,
        allow_duplicate=allow_duplicate,
        forwarding=forwarding,
        hybrid_separators=hybrid_separators,
    )


def count_option(
    keyword: str,
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = None,
    *,
    soft_keyword: bool = False,
    compact_header: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = False,
):
    with option(
        keyword,
        aliases,
        separators,
        header_separators,
        soft_keyword=soft_keyword,
        compact_header=compact_header,
        allow_duplicate=True,
        forwarding=forwarding,
        hybrid_separators=hybrid_separators,
    ):
        return header_fragment(default=0, receiver=CountRx())


def level_short_option(
    keyword: str,
    repeat_chars: str,
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = None,
    *,
    soft_keyword: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = False,
):
    def validator(x):
        if not isinstance(x, str):
            return False

        return all(i in repeat_chars for i in x)

    with option(
        keyword,
        aliases,
        separators,
        header_separators,
        soft_keyword=soft_keyword,
        compact_header=True,
        allow_duplicate=True,
        forwarding=forwarding,
        hybrid_separators=hybrid_separators,
    ):
        return fragment(default=0, validator=validator, transformer=lambda x: len(x), receiver=AddRx())
