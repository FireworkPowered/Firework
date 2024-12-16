from __future__ import annotations

from dataclasses import MISSING
from typing import TYPE_CHECKING, Any, Callable

from elaina_segment import SEPARATORS

from .core.model.receiver import AddRx, CountRx, Rx
from .specifiers import fragment, fragment_union, header_fragment, option

if TYPE_CHECKING:
    from .core.model.capture import Capture


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
        return fragment_union(
            header_fragment(default=0, transformer=lambda _: 0, receiver=AddRx()),
            fragment(default=0, validator=validator, transformer=lambda x: len(x), receiver=AddRx()),
        )


def single_slot_option(
    keyword: str,
    default: Any = MISSING,
    default_factory: Callable[[], Any] = MISSING,  # type: ignore
    aliases: list[str] | None = None,
    separators: str = SEPARATORS,
    header_separators: str | None = "=",
    capture: Capture | None = None,
    receiver: Rx[Any] | None = None,
    validator: Callable[[Any], bool] | None = None,
    transformer: Callable[[Any], Any] | None = None,
    *,
    allow_duplicate: bool = False,
    soft_keyword: bool = False,
    compact_header: bool = False,
    forwarding: bool = True,
    hybrid_separators: bool = True,
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
        return fragment(
            default=default,
            default_factory=default_factory,
            capture=capture,
            receiver=receiver,
            validator=validator,
            transformer=transformer,
        )


# def conflicts(*dc_fields: Field):
#     flatten_twins = UnionMetadata.get_strict(fragment_union(*dc_fields)).twins
#     groups: list[FragmentGroup] = []

#     for ix, (_, fragment_meta) in enumerate(flatten_twins):
#         # Create a group for each field
#         fragment_meta.group = FragmentGroup(ident=f"conflicts_group_{ix}")
#         groups.append(fragment_meta.group)

#     for ix, group in enumerate(groups):
#         # NOTE: Required mangle group ident for each group
#         group.rejects = groups[:ix] + groups[ix + 1 :]

#     return fragment_union(*dc_fields)
