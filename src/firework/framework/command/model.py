from __future__ import annotations

from collections import ChainMap
from dataclasses import MISSING, Field, dataclass, is_dataclass
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING, ClassVar, Iterable, TypeVar, cast, dataclass_transform

from elaina_segment import SEPARATORS, Buffer

from firework.util import Some

from .core.analyzer import Rejected, analyze_loopflow
from .core.model.fragment import Fragment, FragmentGroup
from .core.model.pattern import OptionPattern, SubcommandPattern
from .core.model.snapshot import AnalyzeSnapshot, ProcessingState
from .globals import (
    GLBOAL_SUBCOMMANDS,
    GLOBAL_OPTIONS_BIND,
    YANAGI_INHERITED_OPTIONS,
    YANAGI_INHERITED_SUBCOMMANDS,
)
from .metadata import FragmentMetadata, OptionMetadata, SubcommandMetadata, UnionMetadata
from .specifiers import fragment, fragment_union, header_fragment

if TYPE_CHECKING:
    from .globals import FieldTwin

T = TypeVar("T")


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
        inherited = YANAGI_INHERITED_SUBCOMMANDS.get()
        result = ChainMap({}, GLBOAL_SUBCOMMANDS)

        if inherited is not None:
            result.maps.insert(1, inherited)

        return result

    @classmethod
    def _options_bind_factory(cls, options: list[OptionPattern]):
        inherited = YANAGI_INHERITED_OPTIONS.get()
        result = ChainMap({i.keyword: i for i in options}, GLOBAL_OPTIONS_BIND)

        if inherited is not None:
            result.maps.insert(1, inherited)

        return result

    @classmethod
    def _sistana_fragment_factory(cls, dc_field: Field, metadata: FragmentMetadata):
        f = Fragment(
            name=cls._mangle_name(dc_field.name),
            group=metadata.group,
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
        command_header_fragment = cast("FieldTwin | None", None)
        command_fragments: list[FieldTwin] = []
        option_headers: dict[OptionMetadata, FieldTwin] = {}
        option_fragments_map: dict[OptionMetadata, list[FieldTwin]] = {}
        fragment_groups: list[FragmentGroup] = []

        def _unpack_field_metadata(dc_field: Field, fragment_meta: FragmentMetadata):
            nonlocal command_header_fragment, command_fragments, option_headers, option_fragments_map

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

        for dc_field in fields:
            union_guess = UnionMetadata.get(dc_field)

            if union_guess is not None:
                for field_ref, fragment_meta in union_guess.twins:
                    field_ref.name = dc_field.name

                    _unpack_field_metadata(field_ref, fragment_meta)

                    # Gather fragment groups
                    if fragment_meta.group is not None:
                        fragment_groups.append(fragment_meta.group)
            else:
                fragment_meta = FragmentMetadata.get_or_default(dc_field)
                _unpack_field_metadata(dc_field, fragment_meta)

                # Gather fragment groups
                if fragment_meta.group is not None:
                    fragment_groups.append(fragment_meta.group)

        # Build Sistana fragments

        # 0) Mangled Names, to avoid fragment assignes conflict among different models.
        cls.__yanagi_mangled_names__ = {}

        # 1) Fragments on Command Track

        command_fragments_sistana: list[Fragment] = [
            cls._sistana_fragment_factory(dc_field, fragment_meta) for dc_field, fragment_meta in command_fragments
        ]

        # 2) Fragments on Option Track
        options_sistana: dict[OptionMetadata, list[Fragment]] = {}

        for option_meta, option_fragments in option_fragments_map.items():
            options_sistana[option_meta] = [
                cls._sistana_fragment_factory(dc_field, fragment_meta) for dc_field, fragment_meta in option_fragments
            ]

        # 3) Option Header Fragments
        option_headers_sistana: dict[OptionMetadata, Fragment] = {}

        for option_meta, (dc_field, fragment_meta) in option_headers.items():
            option_headers_sistana[option_meta] = cls._sistana_fragment_factory(dc_field, fragment_meta)

        # 4) Subcommand Header Fragment
        command_header_fragment_sistana = None

        if command_header_fragment is not None:
            dc_field, fragment_meta = command_header_fragment
            command_header_fragment_sistana = cls._sistana_fragment_factory(dc_field, fragment_meta)

        # Post-process fragment groups, mangle names.

        for group in fragment_groups:
            group.ident = cls._mangle_name(group.ident)
            # group.rejects = [cls._mangle_name(i) for i in group.rejects]

        # Build Sistana Command Pattern
        command_meta = cls.__yanagi_subcommand_metadata__

        cls.__sistana_subcommands_bind__ = cls._subcommands_bind_factory()
        cls.__sistana_pattern__ = command_pattern = SubcommandPattern.build(
            command_meta.keyword,
            *command_fragments_sistana,
            aliases=command_meta.aliases,
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
        response = analyze_loopflow(snapshot, buffer)

        if isinstance(response, Rejected):
            raise ValueError(f"Command analysis failed (reason = {response.reason})") from response.exception

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

        # TODO: YanagiParseResult class
        return command_models

    @classmethod
    def register_to(cls, command: type[YanagiCommandBase]):
        command.get_command_pattern().subcommand_from_pattern(cls.get_command_pattern())
        return cls


# NOTE: field specifiers should be updated when new added.
@dataclass_transform(field_specifiers=(fragment, header_fragment, fragment_union))
class YanagiCommand(YanagiCommandBase):
    def __init_subclass__(
        cls,
        *,
        keyword: str,
        aliases: Iterable[str] = (),
        prefixes: Iterable[str] = (),
        separators: str = SEPARATORS,
        soft_keyword: bool = False,
        compact_header: bool = False,
        enter_instantly: bool = False,
    ) -> None:
        dataclass(cls)  # Ensure cls is a dataclass

        cls.__yanagi_subcommand_metadata__ = SubcommandMetadata(
            keyword=keyword,
            aliases=aliases,
            prefixes=prefixes,
            separators=separators,
            soft_keyword=soft_keyword,
            compact_header=compact_header,
            enter_instantly=enter_instantly,
        )
        cls.get_command_pattern()
