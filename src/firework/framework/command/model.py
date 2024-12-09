from __future__ import annotations

from collections import ChainMap
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import MISSING, Field, dataclass, field, is_dataclass
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, TypeAlias, dataclass_transform

from elaina_segment import SEPARATORS, Buffer

from firework.util import Some, cvar

from .core.analyzer import LoopflowExitReason, analyze_loopflow
from .core.model.fragment import Fragment
from .core.model.pattern import OptionPattern, SubcommandPattern
from .core.model.snapshot import AnalyzeSnapshot, ProcessingState

if TYPE_CHECKING:
    from .core.model.capture import Capture
    from .core.model.receiver import Rx

METADATA_IDENT = "yanagi_metadata"

FieldTwin: TypeAlias = "tuple[Field[Any], FragmentMetadata]"

YANAGI_CURRENT_OPTION: ContextVar[OptionMetadata | None] = ContextVar("YANAGI_CURRENT_OPTION", default=None)

GLBOAL_SUBCOMMANDS: ChainMap[str, SubcommandPattern] = ChainMap()
GLOBAL_OPTIONS_BIND: ChainMap[str, OptionPattern] = ChainMap()


@dataclass
class FragmentMetadata:
    variadic: bool = False
    separators: str | None = None
    hybrid_separators: bool = True

    owned_option: OptionMetadata | None = None
    is_header: bool = False

    capture: Capture | None = None
    receiver: Rx[Any] | None = None
    validator: Callable[[Any], bool] | None = None
    transformer: Callable[[Any], Any] | None = None


@dataclass
class SubcommandMetadata:
    keyword: str
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
            METADATA_IDENT: FragmentMetadata(
                variadic=variadic,
                separators=separators,
                hybrid_separators=hybrid_separators,
                owned_option=YANAGI_CURRENT_OPTION.get(),
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


# TODO: more useful field specifiers, which compares to argparse's functions


def _default_fragment_factory():
    return FragmentMetadata()


class YanagiCommandBase:
    # Instance Variables
    __sistana_snapshot__: AnalyzeSnapshot

    # Yanagi Model Metadata
    __yanagi_subcommand_metadata__: ClassVar[SubcommandMetadata]
    __yanagi_mangled_names__: ClassVar[dict[str, str]]

    # Sistana Pattern
    __sistana_pattern__: ClassVar[SubcommandPattern]

    # Sistana Bindings
    __sistana_subcommands_bind__: ClassVar[ChainMap[str, SubcommandPattern]]
    __sistana_options_bind__: ClassVar[ChainMap[str, OptionPattern]]

    @classmethod
    def _mangle_name(cls, name: str):
        return f"_{cls.__name__}__{name}"

    @classmethod
    def _subcommands_bind_factory(cls):
        return ChainMap({}, GLBOAL_SUBCOMMANDS)

    @classmethod
    def _options_bind_factory(cls, options: list[OptionPattern]):
        return ChainMap({i.keyword: i for i in options}, GLOBAL_OPTIONS_BIND)

    @classmethod
    def _sistana_fragment_factory(cls, dc_field: Field, metadata: FragmentMetadata):
        f = Fragment(
            name=cls._mangle_name(dc_field.name),
            variadic=metadata.variadic,
            separators=metadata.separators,
            hybrid_separators=metadata.hybrid_separators,
            validator=metadata.validator,
            transformer=metadata.transformer,
        )

        if metadata.capture is not None:
            f.capture = metadata.capture

        if metadata.receiver is not None:
            f.receiver = metadata.receiver

        if dc_field.default is not MISSING:
            f.default = Some(dc_field.default)
        elif dc_field.default_factory is not MISSING:
            f.default_factory = dc_field.default_factory

        cls.__yanagi_mangled_names__[f.name] = dc_field.name

        return f

    @classmethod
    def get_command_pattern(cls):
        # If pattern is already generated then return it.
        if hasattr(cls, "__sistana_pattern__"):
            return cls.__sistana_pattern__

        # If generated pattern is not found then generate.

        # Before generating from a "class", check if the class is a dataclass.
        # Dataclass provides a good-enough base to do these stuffs, e.g. (ordered) fields.
        if not is_dataclass(cls):
            raise TypeError("Command class must be a dataclass")

        fields = dc_fields(cls)

        # Split fields into command fragments and option fragments.
        command_header_fragment: FieldTwin | None = None
        command_fragments: list[FieldTwin] = []
        option_headers: dict[OptionMetadata, FieldTwin] = {}
        option_fragments_map: dict[OptionMetadata, list[FieldTwin]] = {}

        for dc_field in fields:
            if METADATA_IDENT not in dc_field.metadata:
                fragment_meta = _default_fragment_factory()

            fragment_meta: FragmentMetadata = dc_field.metadata[METADATA_IDENT]

            if fragment_meta.owned_option is None:
                # Subcommand Header Fragment
                if fragment_meta.is_header:
                    if command_header_fragment is not None:
                        raise AttributeError("Header fragment is already defined for the command")

                    command_header_fragment = (dc_field, fragment_meta)
                else:
                    command_fragments.append((dc_field, fragment_meta))
            else:
                # Option Declaration happens here.
                if fragment_meta.owned_option not in option_fragments_map:
                    option_fragments = option_fragments_map[fragment_meta.owned_option] = []
                else:
                    option_fragments = option_fragments_map[fragment_meta.owned_option]

                # Option Header Fragment
                if fragment_meta.is_header:
                    if fragment_meta.owned_option in option_headers:
                        raise AttributeError("Header fragment is already defined for the option")

                    option_headers[fragment_meta.owned_option] = (dc_field, fragment_meta)
                else:
                    option_fragments.append((dc_field, fragment_meta))

        # Build Sistana fragments

        # 0) Mangled Names, to avoid fragment assignes conflict among different models.
        cls.__yanagi_mangled_names__ = {}

        # 1) Fragments on Command Track

        command_fragments_sistana: list[Fragment] = []

        for dc_field, fragment_meta in command_fragments:
            command_fragments_sistana.append(cls._sistana_fragment_factory(dc_field, fragment_meta))

        # 2) Fragments on Option Track
        options_sistana: dict[OptionMetadata, list[Fragment]] = {}

        for option_meta, option_fragments in option_fragments_map.items():
            option_fragments_sistana: list[Fragment] = []

            for dc_field, fragment_meta in option_fragments:
                option_fragments_sistana.append(cls._sistana_fragment_factory(dc_field, fragment_meta))

            options_sistana[option_meta] = option_fragments_sistana

        # 3) Option Header Fragments
        option_headers_sistana: dict[OptionMetadata, Fragment] = {}

        for option_meta, (dc_field, fragment_meta) in option_headers.items():
            option_headers_sistana[option_meta] = cls._sistana_fragment_factory(dc_field, fragment_meta)

        # 4) Subcommand Header Fragment
        command_header_fragment_sistana = None

        if command_header_fragment is not None:
            dc_field, fragment_meta = command_header_fragment
            command_header_fragment_sistana = cls._sistana_fragment_factory(dc_field, fragment_meta)

        # Build Sistana Command Pattern
        command_meta = cls.__yanagi_subcommand_metadata__

        cls.__sistana_subcommands_bind__ = cls._subcommands_bind_factory()
        cls.__sistana_pattern__ = command_pattern = SubcommandPattern.build(
            command_meta.keyword,
            *command_fragments_sistana,
            prefixes=command_meta.prefixes,
            separators=command_meta.separators,
            soft_keyword=command_meta.soft_keyword,
            compact_header=command_meta.compact_header,
            enter_instantly=command_meta.enter_instantly,
            header_fragment=command_header_fragment_sistana,
            subcommands_bind=cls.__sistana_subcommands_bind__,
        )
        command_pattern.__yanagi_model__ = cls  # type: ignore

        # Create "real" options on the command pattern.
        for option_meta, fragments in options_sistana.items():
            command_pattern.option(
                option_meta.keyword,
                *fragments,
                aliases=option_meta.aliases[1:],
                separators=option_meta.separators,
                hybrid_separators=option_meta.hybrid_separators,
                soft_keyword=option_meta.soft_keyword,
                allow_duplicate=option_meta.allow_duplicate,
                compact_header=option_meta.compact_header,
                header_separators=option_meta.header_separators,
                forwarding=option_meta.forwarding,
                header_fragment=option_headers_sistana.get(option_meta),
            )

        # FIXME: a tricky way, expects that the command pattern is already built and no change will be made later.
        #        only refactor sistana/core to support this usage.
        command_pattern._options = cls._options_bind_factory(command_pattern._options).values()  # type: ignore

        return command_pattern

    @classmethod
    def create_snapshot(cls, state: ProcessingState):
        return cls.__sistana_pattern__.create_snapshot(state)

    @classmethod
    def parse(cls, buffer: Buffer, state: ProcessingState = ProcessingState.PREFIX):
        snapshot = cls.create_snapshot(state)
        reason = analyze_loopflow(snapshot, buffer)

        if reason != LoopflowExitReason.satisfied:
            raise ValueError(f"Command analysis failed: {reason}")

        command_models: dict[type[YanagiCommandBase], YanagiCommandBase] = {}
        current_command_model_cls = cls

        for command_node in snapshot.command:
            if command_models:
                current_command_model_cls: type[YanagiCommandBase] = current_command_model_cls.__sistana_subcommands_bind__[
                    command_node
                ].__yanagi_model__  # type: ignore

            assignes = {}

            for k in list(snapshot.mix.assignes):
                if k in current_command_model_cls.__yanagi_mangled_names__:
                    assignes[current_command_model_cls.__yanagi_mangled_names__[k]] = snapshot.mix.assignes.pop(k)

            model = current_command_model_cls(**assignes)
            model.__sistana_snapshot__ = snapshot
            command_models[current_command_model_cls] = model

        return command_models

    @classmethod
    def register_to(cls, command: type[YanagiCommandBase]):
        command.get_command_pattern().subcommand_from_pattern(cls.get_command_pattern())
        return cls


@dataclass_transform(field_specifiers=(fragment, header_fragment))
class YanagiCommand(YanagiCommandBase):
    def __init_subclass__(
        cls,
        *,
        keyword: str,
        prefixes: Iterable[str] = (),
        separators: str = SEPARATORS,
        soft_keyword: bool = False,
        compact_header: bool = False,
        enter_instantly: bool = False,
    ) -> None:
        dataclass(cls)  # Ensure cls is a dataclass

        cls.__yanagi_subcommand_metadata__ = SubcommandMetadata(
            keyword=keyword,
            prefixes=prefixes,
            separators=separators,
            soft_keyword=soft_keyword,
            compact_header=compact_header,
            enter_instantly=enter_instantly,
        )
        cls.get_command_pattern()
