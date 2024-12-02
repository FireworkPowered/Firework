from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from .mix import Mix

if TYPE_CHECKING:
    from tarina.trie import Trie

    from .pattern import OptionPattern, SubcommandPattern


class ProcessingState(int, Enum):
    COMMAND = 0
    PREFIX = 1
    HEADER = 2
    OPTION = 3


class AnalyzeSnapshot:
    __slots__ = (
        "_pending_options",
        "_ref_cache_option",
        "command",
        "endpoint",
        "mix",
        "option",
        "state",
        "traverses",
    )

    state: ProcessingState
    command: list[str]
    option: tuple[tuple[str, ...], str] | None

    traverses: dict[tuple[str, ...], SubcommandPattern]
    endpoint: tuple[str, ...] | None
    mix: Mix

    _pending_options: list[
        tuple[OptionPattern, tuple[str, ...], set[str] | Trie[str], str | None]
    ]  # (pattern, owner, triggers, header-separator)
    _ref_cache_option: dict[tuple[tuple[str, ...], str], OptionPattern]

    def __init__(
        self,
        command: list[str],
        traverses: dict[tuple[str, ...], SubcommandPattern],
        state: ProcessingState = ProcessingState.COMMAND,
    ):
        self.command = command
        self.state = state

        self.traverses = traverses
        self.endpoint = None
        self.mix = Mix()
        self._pending_options = []
        self._ref_cache_option = {}

        self._update_pending_options(tuple(command), traverses[tuple(command)])

    @property
    def context(self):
        return self.traverses[tuple(self.command)]

    def enter_subcommand(self, trigger: str, pattern: SubcommandPattern):
        self.command.append(pattern.header)
        self.state = ProcessingState.COMMAND
        self.option = None

        key = tuple(self.command)
        self.traverses[key] = pattern

        self.mix.update(key, pattern.preset)
        track = self.mix.command_tracks[key]
        track.emit_header(self.mix, trigger)

        self._update_pending_options(key, pattern)

    def enter_option(
        self,
        trigger: str,
        owned_command: tuple[str, ...],
        option_keyword: str,
        pattern: OptionPattern,
    ):
        track = self.mix.option_tracks[owned_command, option_keyword]

        if track.emitted and not pattern.allow_duplicate:
            return False

        track.emit_header(self.mix, trigger)

        if track:
            track.reset()

            self.state = ProcessingState.OPTION
            self.option = owned_command, option_keyword
            self._ref_cache_option[self.option] = pattern

        return True

    @property
    def determined(self):
        return self.endpoint is not None

    @property
    def stage_satisfied(self):
        cmd = tuple(self.command)
        cond = self.mix.command_tracks[cmd].satisfied
        if cond:
            subcommand = self.context
            for option, owner, _, _ in self._pending_options:
                if option.keyword in subcommand._exit_options and not self.mix.option_tracks[owner, option.keyword].satisfied:
                    return False

        return cond

    def determine(self):
        self.state = ProcessingState.COMMAND
        self.endpoint = tuple(self.command)

    def _update_pending_options(self, owner: tuple[str, ...], pattern: SubcommandPattern):
        exit_options = pattern._exit_options

        self._pending_options = [
            (option, owner, triggers, separators)
            for option, option_owner, triggers, separators in self._pending_options
            if not (owner == option_owner and option.keyword in exit_options)
        ] + [
            (option, owner, option._trigger, option.header_separators)  # type: ignore
            for option in pattern._options
        ]

    def get_subcommand(self, context: SubcommandPattern, val: str):
        if val in context._subcommands_bind:
            return context._subcommands_bind[val], None

        if context._compact_keywords is not None:
            prefix = context._compact_keywords.longest_prefix(val).key
            if prefix is not None:
                return context._subcommands_bind[prefix], val[len(prefix) :]

    def get_option(self, val: str):
        for option, owner, triggers, separator in self._pending_options:
            if option.compact_header:
                prefix = triggers.longest_prefix(val).key  # type: ignore
                if prefix is not None:
                    return option, owner, val[len(prefix) :]
            elif val in triggers:
                return option, owner, None

            if separator is not None:
                keyword, *tail = val.split(separator, 1)
                if keyword in triggers:
                    return option, owner, tail[0] if tail else None
