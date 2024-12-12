from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

from firework.util import Maybe, Some

from ..err import CaptureRejected, ReceivePanic, TransformPanic, ValidateRejected
from .fragment import Fragment, assert_fragments_order

if TYPE_CHECKING:
    from elaina_segment import Buffer


class Track:
    __slots__ = ("cursor", "emitted", "fragments", "header", "max_length")

    header: Fragment | None
    fragments: tuple[Fragment, ...]
    cursor: int
    max_length: int
    emitted: bool

    def __init__(self, fragments: tuple[Fragment, ...], header: Fragment | None = None):
        self.fragments = fragments
        self.header = header
        self.cursor = 0
        self.max_length = len(self.fragments)
        self.emitted = False

    @property
    def satisfied(self):
        return (
            self.cursor >= self.max_length or self.fragments[self.cursor].default is not None or self.fragments[self.cursor].variadic
        )

    def complete(self, mix: Mix):
        if self.header is not None and self.header.name not in mix.assignes and self.header.default is not None:
            mix.assignes[self.header.name] = self.header.default.value

        if self.cursor >= self.max_length:
            return

        for frag in self.fragments[self.cursor :]:
            if frag.name not in mix.assignes:
                if frag.default is not None:
                    mix.assignes[frag.name] = frag.default.value
                elif frag.default_factory is not None:
                    mix.assignes[frag.name] = frag.default_factory()

        last = self.fragments[-1]
        if last.variadic and last.name not in mix.assignes:
            mix.assignes[last.name] = []

    def fetch(
        self,
        mix: Mix,
        frag: Fragment,
        buffer: Buffer,
        upper_separators: str,
    ):
        tail = cast(Maybe[Any], None)
        token = None

        def rxfetch():
            nonlocal tail, token

            if frag.separators is not None:
                if frag.hybrid_separators:
                    separators = frag.separators + upper_separators
                else:
                    separators = frag.separators
            else:
                separators = upper_separators

            val, tail, token = frag.capture.capture(buffer, separators)

            if frag.validator is not None and not frag.validator(val):
                raise ValidateRejected(f"Validation failed for {frag.name}, got {val}")

            if frag.transformer is not None:
                try:
                    val = frag.transformer(val)
                except Exception as e:
                    raise TransformPanic(f"Failed to transform {frag.name} via {frag.transformer}, got {val}") from e

            return val

        def rxprev():
            if frag.name in mix.assignes:
                return Some(mix.assignes[frag.name])

        if frag.variadic:

            def rxput(val):
                if frag.name not in mix.assignes:
                    mix.assignes[frag.name] = []

                mix.assignes[frag.name].append(val)
        else:

            def rxput(val):
                mix.assignes[frag.name] = val

        try:
            frag.receiver.receive(rxfetch, rxprev, rxput)
        except (CaptureRejected, ValidateRejected, TransformPanic):
            raise
        except Exception as e:
            raise ReceivePanic from e

        if tail is not None:
            buffer.add_to_ahead(tail.value)

        if token is not None:
            token.apply()

    @contextmanager
    def around(self, mix: Mix, fragment: Fragment):
        if fragment.group is not None:
            if fragment.group.ident in mix.rejected_group:
                raise CaptureRejected(f"Group {fragment.group.ident} is rejected")

            yield

            mix.rejected_group.update(fragment.group.rejects)
        else:
            yield

    def forward(
        self,
        mix: Mix,
        buffer: Buffer,
        separators: str,
    ):
        if self.cursor >= self.max_length:
            return

        first = self.fragments[self.cursor]

        with self.around(mix, first):
            self.fetch(mix, first, buffer, separators)

        if not first.variadic:
            self.cursor += 1

        return first

    def emit_header(self, mix: Mix, segment: str):
        self.emitted = True

        if self.header is None:
            return

        header = self.header

        def rxfetch():
            if header.validator is not None and not header.validator(segment):
                raise ValidateRejected(f"Validation failed for {header.name}, got {segment}")

            if header.transformer is not None:
                try:
                    return header.transformer(segment)
                except Exception as e:
                    raise TransformPanic(f"Failed to transform {header.name} via {header.transformer}, got {segment}") from e

            return segment

        def rxprev():
            if header.name in mix.assignes:
                return Some(mix.assignes[header.name])

        def rxput(val):
            mix.assignes[header.name] = val

        with self.around(mix, header):
            try:
                header.receiver.receive(rxfetch, rxprev, rxput)
            except (CaptureRejected, ValidateRejected, TransformPanic):
                raise
            except Exception as e:
                raise ReceivePanic from e

    @property
    def assignable(self):
        return self.cursor < self.max_length

    def copy(self):
        return Track(self.fragments, self.header)

    def reset(self):
        self.cursor = 0

    def __bool__(self):
        return bool(self.fragments)


class Preset:
    __slots__ = ("option_tracks", "subcommand_track")

    subcommand_track: Track
    option_tracks: dict[str, Track]

    def __init__(self, subcommand_track: Track, option_tracks: dict[str, Track]):
        self.subcommand_track = subcommand_track
        self.option_tracks = option_tracks

        assert_fragments_order(subcommand_track.fragments)

        for track in self.option_tracks.values():
            assert_fragments_order(track.fragments)


class Mix:
    __slots__ = ("assignes", "command_tracks", "option_tracks")

    assignes: dict[str, Any]

    command_tracks: dict[tuple[str, ...], Track]
    option_tracks: dict[tuple[tuple[str, ...], str], Track]

    def __init__(self):
        self.assignes = {}
        self.command_tracks = {}
        self.option_tracks = {}

    def complete(self):
        for track in self.command_tracks.values():
            track.complete(self)

    @property
    def satisfied(self):
        for track in self.command_tracks.values():
            if not track.satisfied:
                return False

        return all(track.satisfied for track in self.option_tracks.values())

    def update(self, root: tuple[str, ...], preset: Preset):
        self.command_tracks[root] = preset.subcommand_track.copy()

        for track_id, track in preset.option_tracks.items():
            self.option_tracks[root, track_id] = track.copy()
