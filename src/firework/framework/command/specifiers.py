from __future__ import annotations

from contextlib import contextmanager
from dataclasses import MISSING, Field, field
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from elaina_segment import SEPARATORS

from firework.util import cvar

from .globals import FRAGMENT_METADATA_IDENT, UNION_METADATA_IDENT, YANAGI_CURRENT_FRAGMENT_GROUP, YANAGI_CURRENT_OPTION
from .metadata import FragmentMetadata, OptionMetadata, UnionMetadata

if TYPE_CHECKING:
    from .core.model.capture import Capture
    from .core.model.receiver import Rx
    from .model import YanagiCommandBase

Cmd = TypeVar("Cmd", bound="YanagiCommandBase")


@contextmanager
def option(
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
    with cvar(
        YANAGI_CURRENT_OPTION,
        OptionMetadata(
            keyword,
            aliases or [],
            separators,
            header_separators,
            soft_keyword,
            compact_header,
            allow_duplicate,
            forwarding,
            hybrid_separators,
        ),
    ):
        yield


def fragment(
    *,
    default: Any = MISSING,
    default_factory: Callable[[], Any] = MISSING,  # type: ignore
    variadic: bool = False,
    separators: str | None = None,
    hybrid_separators: bool = True,
    is_header: bool = False,
    capture: Capture | None = None,
    receiver: Rx[Any] | None = None,
    validator: Callable[[Any], bool] | None = None,
    transformer: Callable[[Any], Any] | None = None,
):
    return field(
        default=default,
        default_factory=default_factory,
        metadata={
            FRAGMENT_METADATA_IDENT: FragmentMetadata(
                variadic=variadic,
                separators=separators,
                hybrid_separators=hybrid_separators,
                owned_option=YANAGI_CURRENT_OPTION.get(),
                group=YANAGI_CURRENT_FRAGMENT_GROUP.get(),
                is_header=is_header,
                capture=capture,
                receiver=receiver,
                validator=validator,
                transformer=transformer,
            )
        },
    )  # type: ignore


def header_fragment(
    *,
    default: Any = MISSING,
    default_factory: Callable[[], Any] = MISSING,  # type: ignore
    variadic: bool = False,
    separators: str | None = None,
    hybrid_separators: bool = True,
    capture: Capture | None = None,
    receiver: Rx[Any] | None = None,
    validator: Callable[[Any], bool] | None = None,
    transformer: Callable[[Any], Any] | None = None,
):
    return fragment(
        default=default,
        default_factory=default_factory,
        variadic=variadic,
        separators=separators,
        hybrid_separators=hybrid_separators,
        is_header=True,
        capture=capture,
        receiver=receiver,
        validator=validator,
        transformer=transformer,
    )


# def fragment_group(ident: str, rejects: Iterable[str] = ()):
#     with cvar(YANAGI_CURRENT_FRAGMENT_GROUP, FragmentGroup(ident, list(rejects))):
#         yield


def fragment_union(*fragment_fields: Field):
    twins = []

    for dc_field in fragment_fields:
        if UNION_METADATA_IDENT in dc_field.metadata:
            twins.extend(UnionMetadata.get_strict(dc_field).twins)
        else:
            twins.append((dc_field, FragmentMetadata.get(dc_field)))

    return field(metadata={UNION_METADATA_IDENT: UnionMetadata(twins=twins)})


def subcommand_of(host: type[YanagiCommandBase]):
    def wrapper(guest: type[Cmd]) -> type[Cmd]:
        guest.register_to(host)

        return guest

    return wrapper
