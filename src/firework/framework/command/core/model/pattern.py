from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Iterable, MutableMapping

from elaina_segment import SEPARATORS

from firework.util import RadixTrie

from .fragment import assert_fragments_order
from .mix import Preset, Track
from .snapshot import AnalyzeSnapshot, ProcessingState

if TYPE_CHECKING:
    from .fragment import Fragment


@dataclass
class SubcommandPattern:
    header: str
    preset: Preset

    soft_keyword: bool = False
    separators: str = SEPARATORS

    aliases: list[str] = field(default_factory=list)
    prefixes: RadixTrie[str] | None = field(default=None)
    compact_header: bool = False
    enter_instantly: bool = False
    compact_aliases: bool = False
    header_fragment: Fragment | None = None

    _subcommands: MutableMapping[str, SubcommandPattern] = field(default_factory=dict)
    _options: list[OptionPattern] = field(default_factory=list)
    _compact_keywords: RadixTrie[str] | None = field(default=None)

    @classmethod
    def build(
        cls,
        header: str,
        *fragments: Fragment,
        prefixes: Iterable[str] = (),
        compact_header: bool = False,
        enter_instantly: bool = True,
        separators: str = SEPARATORS,
        soft_keyword: bool = False,
        header_fragment: Fragment | None = None,
        subcommands_bind: MutableMapping[str, SubcommandPattern] | None = None,
    ):
        if subcommands_bind is None:
            subcommands_bind = {}

        preset = Preset(Track(fragments, header=header_fragment), {})
        subcommand = cls(
            header=header,
            preset=preset,
            compact_header=compact_header,
            enter_instantly=enter_instantly,
            separators=separators,
            soft_keyword=soft_keyword,
            header_fragment=header_fragment,
            _subcommands=subcommands_bind,
        )

        if prefixes:
            trie = subcommand.prefixes = RadixTrie()  # type: ignore

            for prefix in prefixes:
                trie.set(prefix, prefix)

        return subcommand

    def create_snapshot(self, state: ProcessingState = ProcessingState.COMMAND):
        snapshot = AnalyzeSnapshot(command=[self.header], state=state, traverses={(self.header,): self})
        snapshot.mix.update((self.header,), self.preset)
        return snapshot

    @property
    def root_entrypoint(self):
        return self.create_snapshot()

    @property
    def prefix_entrypoint(self):
        return self.create_snapshot(ProcessingState.PREFIX)

    @property
    def header_entrypoint(self):
        return self.create_snapshot(ProcessingState.HEADER)

    def _add_option_track(self, name: str, fragments: tuple[Fragment, ...], header: Fragment | None = None):
        assert_fragments_order(fragments)

        self.preset.option_tracks[name] = Track(fragments, header=header)

    def subcommand(
        self,
        header: str,
        *fragments: Fragment,
        aliases: Iterable[str] = (),
        soft_keyword: bool = False,
        separators: str = SEPARATORS,
        compact_header: bool = False,
        compact_aliases: bool = False,
        enter_instantly: bool = False,
        header_fragment: Fragment | None = None,
    ):
        preset = Preset(Track(fragments, header=header_fragment), {})
        pattern = SubcommandPattern(
            header=header,
            preset=preset,
            aliases=list(aliases),
            soft_keyword=soft_keyword,
            separators=separators,
            compact_header=compact_header,
            compact_aliases=compact_aliases,
            enter_instantly=enter_instantly,
            header_fragment=header_fragment,
        )

        return self.subcommand_from_pattern(pattern)

    def subcommand_from_pattern(self, pattern: SubcommandPattern):
        self._subcommands[pattern.header] = pattern
        for alias in pattern.aliases:
            self._subcommands[alias] = pattern

        if pattern.compact_header:
            trie = RadixTrie()
            trie.set(pattern.header, pattern.header)

            for alias in pattern.aliases:
                trie.set(alias, alias)

            if self._compact_keywords is not None:
                trie.update(self._compact_keywords.items())

            self._compact_keywords = trie

        return pattern

    def option(
        self,
        keyword: str,
        *fragments: Fragment,
        aliases: Iterable[str] = (),
        separators: str | None = None,
        hybrid_separators: bool = False,
        soft_keyword: bool = False,
        allow_duplicate: bool = False,
        compact_header: bool = False,
        header_fragment: Fragment | None = None,
        header_separators: str | None = None,
        forwarding: bool = True,
    ):
        if separators is None:
            separators = self.separators
        elif hybrid_separators:
            separators = separators + self.separators

        pattern = OptionPattern(
            keyword,
            aliases=list(aliases),
            separators=separators,
            allow_duplicate=allow_duplicate,
            soft_keyword=soft_keyword,
            header_fragment=header_fragment,
            header_separators=header_separators,
            compact_header=compact_header,
            forwarding=forwarding,
        )

        self._options.append(pattern)
        self._add_option_track(keyword, fragments, header=header_fragment)

        if header_separators and not fragments:
            raise ValueError("header_separators must be used with fragments")

        return self


@dataclass
class OptionPattern:
    keyword: str
    aliases: list[str] = field(default_factory=list)
    separators: str = SEPARATORS

    soft_keyword: bool = False
    allow_duplicate: bool = False
    header_fragment: Fragment | None = None
    header_separators: str | None = None
    compact_header: bool = False
    forwarding: bool = True

    @cached_property
    def _trigger(self):
        if self.compact_header:
            trie = RadixTrie[str]()
            trie.set(self.keyword, self.keyword)

            for alias in self.aliases:
                trie.set(alias, alias)

            return trie

        return {self.keyword, *self.aliases}

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self is other
        return NotImplemented

    def __hash__(self):
        return id(self)
