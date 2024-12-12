from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Iterable

from .mix import Mix

if TYPE_CHECKING:
    from .pattern import OptionPattern, SubcommandPattern


class ProcessingState(int, Enum):
    COMMAND = 0
    PREFIX = 1
    HEADER = 2
    OPTION = 3


class AnalyzeSnapshot:
    __slots__ = (
        "available_options",
        "command",
        "endpoint",
        "mix",
        "option",
        "state",
        "traverses",
    )

    # State
    state: ProcessingState
    command: list[str]
    option: tuple[tuple[str, ...], str, OptionPattern] | None

    # Record
    mix: Mix
    endpoint: tuple[str, ...] | None
    traverses: dict[tuple[str, ...], SubcommandPattern]
    available_options: dict[tuple[str, ...], Iterable[OptionPattern]]

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
        self.available_options = {}

        self._options_enter(tuple(command), traverses[tuple(command)])

    @property
    def context(self):
        return self.traverses[tuple(self.command)]

    def enter_subcommand(self, trigger: str, pattern: SubcommandPattern):
        self._options_exit(tuple(self.command))

        self.command.append(pattern.header)
        self.state = ProcessingState.COMMAND
        self.option = None

        key = tuple(self.command)
        self.traverses[key] = pattern
        self.mix.update(key, pattern.preset)

        track = self.mix.command_tracks[key]
        track.emit_header(self.mix, trigger)

        self._options_enter(key, pattern)

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
            self.option = owned_command, option_keyword, pattern

        return True

    @property
    def determined(self):
        return self.endpoint is not None

    @property
    def stage_satisfied(self):
        command_satisfied = self.mix.command_tracks[tuple(self.command)].satisfied

        if command_satisfied:
            for owner, options in self.available_options.items():
                # NOTE: stage satisfied += for all option tracks, either forwarding or satisfied.

                for option in options:
                    if not option.forwarding and not self.mix.option_tracks[owner, option.keyword].satisfied:
                        return False

        return command_satisfied

    def determine(self):
        self.state = ProcessingState.COMMAND
        self.endpoint = tuple(self.command)

    def get_subcommand(self, val: str):
        context = self.context

        if val in context._subcommands:
            return context._subcommands[val], None

        if context._compact_keywords is not None:
            prefix = context._compact_keywords.longest_prefix_key(val)
            if prefix is not None:
                return context._subcommands[prefix], val[len(prefix) :]

    def get_option(self, val: str):
        split_cache = {}

        for owner, options in self.available_options.items():
            for option in options:
                triggers = option._trigger
                separator = option.header_separators

                if option.compact_header:
                    prefix = triggers.longest_prefix_key(val)  # type: ignore
                    if prefix is not None:
                        return option, owner, val[len(prefix) :]
                elif val in triggers:
                    return option, owner, None

                if separator is not None:
                    if separator in split_cache:
                        keyword, *tail = split_cache[separator]
                    else:
                        keyword, *tail = split_cache[separator] = val.split(separator, 1)

                    if keyword in triggers:
                        return option, owner, tail[0] if tail else None

    def _options_enter(self, owner: tuple[str, ...], pattern: SubcommandPattern):
        self.available_options[owner] = pattern._options

    def _options_exit(self, owner: tuple[str, ...]):
        self.available_options[owner] = [x for x in self.available_options[owner] if x.forwarding]
