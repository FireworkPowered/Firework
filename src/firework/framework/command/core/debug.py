from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model.fragment import Fragment
    from .model.mix import Preset, Track
    from .model.pattern import SubcommandPattern

# TODO: Better pretty print


def pretty_fragment(fragment: Fragment):
    phase = fragment.name

    if fragment.default is not None:
        phase = f"[{phase} = {fragment.default.value}]"

    if fragment.variadic:
        phase = f"...{phase}"

    # phase = f"{phase}<separators = {fragment.separators}>"
    meta = {}

    if fragment.separators is not None:
        meta["separators"] = fragment.separators

    if not fragment.hybrid_separators:
        meta["hybrid_separators"] = "no"

    if meta:
        phase = f"{phase}<{', '.join(f'{k} = {v}' for k, v in meta.items())}>"

    return phase


def pretty_track(track: Track):
    content = ", ".join([pretty_fragment(i) for i in track.fragments])

    if track.header is not None:
        content = f"{pretty_fragment(track.header)} | {content}"

    return f"({content})"


def pretty_preset_options(preset: Preset):
    return "\n".join([f"[{name} <: {pretty_track(track)}]" for name, track in preset.option_tracks.items()])


def pretty_pattern(command: SubcommandPattern):
    return f"{command.header} <: {pretty_track(command.preset.subcommand_track)}\n{pretty_preset_options(command.preset)}"
