from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from elaina_segment.err import OutOfData

from .err import ParsePanic, Rejected
from .model.snapshot import AnalyzeSnapshot, ProcessingState

if TYPE_CHECKING:
    from elaina_segment import Buffer

T = TypeVar("T")


class LoopflowExitReason(str, Enum):
    satisfied = "satisfied"
    unsatisfied = "unsatisfied"
    prefix_expect_str = "prefix_expect_str"
    prefix_mismatch = "prefix_mismatch"
    header_expect_str = "header_expect_str"
    header_mismatch = "header_mismatch"
    unexpected_segment = "unexpected_segment"
    option_duplicated_prohibited = "option_duplicated_prohibited"
    expect_forward_subcommand = "expect_forward_subcommand"
    expect_forward_option = "expect_forward_option"
    previous_option_unsatisfied = "previous_option_unsatisfied"
    previous_subcommand_unsatisfied = "previous_subcommand_unsatisfied"

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"<analyze(snapshot, buffer) => {self.value}>"


def analyze_loopflow(snapshot: AnalyzeSnapshot, buffer: Buffer[T]) -> LoopflowExitReason:
    mix = snapshot.mix

    while True:
        state = snapshot.state
        context = snapshot.context

        try:
            token = buffer.next(context.separators)
        except OutOfData:
            if mix.satisfied:
                mix.complete()
                snapshot.determine()
                return LoopflowExitReason.satisfied

            # 这里如果没有 satisfied，如果是 option 的 track，则需要 reset
            # 从 Buffer 吃掉的东西？我才不还。
            if state is ProcessingState.OPTION:
                mix.option_tracks[snapshot.option].reset()  # type: ignore

            return LoopflowExitReason.unsatisfied

        if state is ProcessingState.PREFIX:
            if context.prefixes is not None:
                if not isinstance(token.val, str):
                    return LoopflowExitReason.prefix_expect_str

                if context.prefixes is not None:
                    prefix = context.prefixes.longest_prefix(buffer.first()).key  # type: ignore
                    if prefix is None:
                        return LoopflowExitReason.prefix_mismatch

                    token.apply()
                    buffer.pushleft(token.val[len(prefix) :])

            snapshot.state = ProcessingState.HEADER
            continue
        if state is ProcessingState.HEADER:
            if not isinstance(token.val, str):
                return LoopflowExitReason.header_expect_str

            token.apply()

            if token.val == context.header:
                pass  # do nothing
            elif context.compact_header and token.val.startswith(context.header):
                v = token.val[len(context.header) :]
                if v:
                    buffer.pushleft(v)

            else:
                return LoopflowExitReason.header_mismatch

            track = mix.command_tracks[tuple(snapshot.command)]
            track.emit_header(mix, token.val)

            snapshot.state = ProcessingState.COMMAND
            continue

        if isinstance(token.val, str):
            if (subcommand_info := snapshot.get_subcommand(context, token.val)) is not None:
                subcommand, tail = subcommand_info
                enter_forward = False

                if state is ProcessingState.OPTION:
                    owner, keyword = snapshot.option  # type: ignore
                    current_track = mix.option_tracks[owner, keyword]

                    if current_track.satisfied:
                        current_track.complete(mix)
                    elif not subcommand.soft_keyword:
                        current_track.reset()
                        return LoopflowExitReason.previous_option_unsatisfied
                    else:
                        enter_forward = True

                if not enter_forward:
                    if snapshot.stage_satisfied or subcommand.enter_instantly:
                        token.apply()
                        mix.complete()

                        if tail is not None:
                            buffer.pushleft(tail)

                        snapshot.enter_subcommand(token.val, subcommand)
                        continue
                    if not subcommand.soft_keyword:
                        return LoopflowExitReason.previous_subcommand_unsatisfied

            elif (option_info := snapshot.get_option(token.val)) is not None:
                target_option, target_owner, tail = option_info
                enter_forward = False

                if state is ProcessingState.OPTION:
                    owner, keyword = snapshot.option  # type: ignore
                    current_track = mix.option_tracks[owner, keyword]

                    if current_track.satisfied:
                        current_track.complete(mix)
                        snapshot.state = ProcessingState.COMMAND
                    elif not target_option.soft_keyword:
                        current_track.reset()
                        return LoopflowExitReason.previous_option_unsatisfied
                    else:
                        enter_forward = True

                if not enter_forward and (not target_option.soft_keyword or snapshot.stage_satisfied):
                    if not snapshot.enter_option(token.val, target_owner, target_option.keyword, target_option):
                        return LoopflowExitReason.option_duplicated_prohibited

                    token.apply()

                    if tail is not None:
                        buffer.pushleft(tail)

                    continue

        if state is ProcessingState.COMMAND:
            track = mix.command_tracks[tuple(snapshot.command)]

            try:
                response = track.forward(mix, buffer, context.separators)
            except OutOfData:
                return LoopflowExitReason.expect_forward_subcommand
            except (Rejected, ParsePanic):
                raise
            except Exception as e:
                raise ParsePanic from e
            else:
                if response is None:
                    # track 上没有 fragments 可供分配了, 此时又没有再流转到其他 traverse
                    return LoopflowExitReason.unexpected_segment
        else:
            track = mix.option_tracks[snapshot.option]  # type: ignore
            opt = snapshot._ref_cache_option[snapshot.option]  # type: ignore

            try:
                response = track.forward(mix, buffer, opt.separators)
            except OutOfData:
                track.reset()
                return LoopflowExitReason.expect_forward_option
            except (Rejected, ParsePanic):
                raise
            except Exception as e:
                raise ParsePanic from e
            else:
                if response is None:
                    snapshot.state = ProcessingState.COMMAND
