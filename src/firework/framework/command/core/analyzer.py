from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeAlias, TypeVar

from elaina_segment.err import OutOfData

from .err import ParsePanic, ParseRejected
from .model.snapshot import AnalyzeSnapshot, ProcessingState

if TYPE_CHECKING:
    from elaina_segment import Buffer

T = TypeVar("T")

LoopflowResult: TypeAlias = "Accepted[T] | Rejected[T]"


class LoopflowRejectReason(str, Enum):
    component_rejected = "component_rejected"
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


@dataclass
class Accepted(Generic[T]):
    snapshot: AnalyzeSnapshot
    buffer: Buffer[T]

    @property
    def mix(self):
        return self.snapshot.mix

    # TODO: more adorable methods


@dataclass
class Rejected(Generic[T]):
    reason: LoopflowRejectReason
    exception: BaseException | None

    snapshot: AnalyzeSnapshot
    buffer: Buffer[T]


def analyze_loopflow(snapshot: AnalyzeSnapshot, buffer: Buffer[T]) -> LoopflowResult[T]:
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
                return Accepted(snapshot, buffer)

            # NOTE: If the option track is not satisfied, it will be reset.
            #       Consumed data will not return back to the buffer.
            if state is ProcessingState.OPTION:
                owner, keyword, _ = snapshot.option  # type: ignore
                mix.option_tracks[owner, keyword].reset()  # type: ignore

            return Rejected(
                reason=LoopflowRejectReason.unsatisfied,
                exception=None,
                snapshot=snapshot,
                buffer=buffer,
            )

        if state is ProcessingState.PREFIX:
            if context.prefixes is not None:
                if not isinstance(token.val, str):
                    return Rejected(
                        reason=LoopflowRejectReason.prefix_expect_str,
                        exception=None,
                        snapshot=snapshot,
                        buffer=buffer,
                    )

                if context.prefixes is not None:
                    prefix = context.prefixes.longest_prefix_key(buffer.first())  # type: ignore
                    if prefix is None:
                        return Rejected(
                            reason=LoopflowRejectReason.prefix_mismatch,
                            exception=None,
                            snapshot=snapshot,
                            buffer=buffer,
                        )

                    token.apply()
                    buffer.pushleft(token.val[len(prefix) :])

            snapshot.state = ProcessingState.HEADER
            continue
        if state is ProcessingState.HEADER:
            if not isinstance(token.val, str):
                return Rejected(
                    reason=LoopflowRejectReason.header_expect_str,
                    exception=None,
                    snapshot=snapshot,
                    buffer=buffer,
                )

            token.apply()

            if token.val == context.header:
                # NOTE: Segment is exact header and no required additional processing.
                pass
            elif context.compact_header and token.val.startswith(context.header):
                # NOTE: Segment could be a compact header.
                #       Tail of the segment should be pushed back to the buffer.
                v = token.val[len(context.header) :]
                if v:
                    buffer.pushleft(v)

            else:
                # NOTE: Segment is not header.

                return Rejected(
                    reason=LoopflowRejectReason.header_mismatch,
                    exception=None,
                    snapshot=snapshot,
                    buffer=buffer,
                )

            track = mix.command_tracks[tuple(snapshot.command)]
            track.emit_header(mix, token.val)

            snapshot.state = ProcessingState.COMMAND
            continue

        if isinstance(token.val, str):
            if (subcommand_info := snapshot.get_subcommand(token.val)) is not None:
                subcommand, tail = subcommand_info
                enter_forward = False  # let's took more semantical.

                if state is ProcessingState.OPTION:
                    # NOTE: Option -> Subcommand, should check if the current option is satisfied.

                    # NOTE: "_" is current option, reversed for the future.
                    owner, keyword, _ = snapshot.option  # type: ignore
                    current_track = mix.option_tracks[owner, keyword]

                    if current_track.satisfied:
                        current_track.complete(mix)
                    elif not subcommand.soft_keyword:
                        current_track.reset()

                        return Rejected(
                            reason=LoopflowRejectReason.previous_option_unsatisfied,
                            exception=None,
                            snapshot=snapshot,
                            buffer=buffer,
                        )
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
                        return Rejected(
                            reason=LoopflowRejectReason.previous_subcommand_unsatisfied,
                            exception=None,
                            snapshot=snapshot,
                            buffer=buffer,
                        )

            elif (option_info := snapshot.get_option(token.val)) is not None:
                target_option, target_owner, tail = option_info
                enter_forward = False

                if state is ProcessingState.OPTION:
                    # NOTE: Option -> Option, should check if the current option is satisfied.

                    # NOTE: "_" is current option, reversed for the future.
                    owner, keyword, _ = snapshot.option  # type: ignore
                    current_track = mix.option_tracks[owner, keyword]

                    if current_track.satisfied:
                        current_track.complete(mix)
                        snapshot.state = ProcessingState.COMMAND
                    elif not target_option.soft_keyword:
                        current_track.reset()

                        return Rejected(
                            reason=LoopflowRejectReason.previous_option_unsatisfied,
                            exception=None,
                            snapshot=snapshot,
                            buffer=buffer,
                        )
                    else:
                        enter_forward = True

                if not enter_forward and (not target_option.soft_keyword or snapshot.stage_satisfied):
                    # NOTE: "soft_keyword and not stage_satisfied" means the "option" token should be treated as Fragment value.

                    if not snapshot.enter_option(token.val, target_owner, target_option.keyword, target_option):
                        return Rejected(
                            reason=LoopflowRejectReason.option_duplicated_prohibited,
                            exception=None,
                            snapshot=snapshot,
                            buffer=buffer,
                        )

                    token.apply()

                    if tail is not None:
                        buffer.pushleft(tail)

                    continue

        if state is ProcessingState.COMMAND:
            track = mix.command_tracks[tuple(snapshot.command)]
            separators = context.separators

            try:
                hit_fragment = track.forward(mix, buffer, separators)
            except OutOfData:
                return Rejected(
                    reason=LoopflowRejectReason.expect_forward_subcommand,
                    exception=None,
                    snapshot=snapshot,
                    buffer=buffer,
                )
            except ParsePanic:
                raise
            except ParseRejected as e:
                return Rejected(
                    reason=LoopflowRejectReason.component_rejected,
                    exception=e,
                    snapshot=snapshot,
                    buffer=buffer,
                )
            except Exception as e:
                raise ParsePanic("Unexpected error occurred during sistana parsing") from e
            else:
                if hit_fragment is None:
                    # NOTE: No fragments to assign on the track, and no further traverse to flow.
                    #       This means user input is unexpected (too long often).

                    return Rejected(
                        reason=LoopflowRejectReason.unexpected_segment,
                        exception=None,
                        snapshot=snapshot,
                        buffer=buffer,
                    )
        else:
            owner, keyword, opt = snapshot.option  # type: ignore
            track = mix.option_tracks[owner, keyword]  # type: ignore
            separators = opt.separators

            try:
                hit_fragment = track.forward(mix, buffer, separators)
            except OutOfData:
                # NOTE: For option fragments, "prompt" is unavailable so consumed data won't back.
                #       (Sistana cannot treat soft keyword consistently.)
                track.reset()

                return Rejected(
                    reason=LoopflowRejectReason.expect_forward_option,
                    exception=None,
                    snapshot=snapshot,
                    buffer=buffer,
                )
            except ParsePanic:
                raise
            except ParseRejected as e:
                return Rejected(
                    reason=LoopflowRejectReason.component_rejected,
                    exception=e,
                    snapshot=snapshot,
                    buffer=buffer,
                )
            except Exception as e:
                raise ParsePanic("Unexpected error occurred during sistana parsing") from e
            else:
                if hit_fragment is None:
                    snapshot.state = ProcessingState.COMMAND

                    # NOTE: No fragments to assign on the track, and no further traverse to flow.
                    #       Here folds the buffer next operation (usually a segment_once), which is a slow path.
                    buffer.add_to_ahead(token.val)
                    token.apply()
