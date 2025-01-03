from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import TypedDict, cast

_LIG = r"[A-Za-z0-9_-]"
_L_REP = rf"({_LIG}+\.)*"
_R_REP = rf"(\.{_LIG}+)*"
SOURCE_REGEX = re.compile(rf"(?P<prefix>{_L_REP}){{(?P<sect_prefix>{_L_REP})\*\*(?P<sect_suffix>{_R_REP})}}(?P<suffix>{_R_REP})")


@dataclass
class SectionSpec:
    prefix: list[str]
    suffix: list[str]


@dataclass
class SourceSpec:
    prefix: list[str]
    suffix: list[str]
    section: SectionSpec


class SourceRegexGroup(TypedDict):
    prefix: str
    sect_prefix: str
    sect_suffix: str
    suffix: str


def parse_source(spec: str) -> SourceSpec:
    if not (match_res := SOURCE_REGEX.fullmatch(spec)):
        raise ValueError(f"{spec!r} doesn't match {SOURCE_REGEX.pattern!r}")
    groups: SourceRegexGroup = cast(SourceRegexGroup, match_res.groupdict())
    section: SectionSpec = SectionSpec(groups["sect_prefix"].split(".")[:-1], groups["sect_suffix"].split(".")[1:])
    return SourceSpec(
        groups["prefix"].split(".")[:-1] + section.prefix,
        section.suffix + groups["suffix"].split(".")[1:],
        section,
    )


class PathFill(enum.Enum):
    SINGLE = enum.auto()  # {} or {*}
    EXTEND = enum.auto()  # {**}


@dataclass
class PathSpec:
    path: list[str | PathFill]
    section: list[str | PathFill]

    @property
    def fill_lens(self) -> tuple[int, int]:
        fills = [i for i in self.path + self.section if isinstance(i, PathFill)]
        if PathFill.EXTEND not in fills:
            return len(fills), 0
        ext_ind = fills.index(PathFill.EXTEND)
        return ext_ind, len(fills) - ext_ind - 1

    def format(self, parts: list[str]) -> DestWithMount | None:
        front_len, back_len = self.fill_lens
        front = parts[:front_len]
        back = parts[front_len:][-back_len or len(parts) :]
        ext = parts[front_len : -back_len or len(parts)]
        if len(front) != front_len or len(back) != back_len or (ext and PathFill.EXTEND not in self.path + self.section):
            return
        formatted_it = iter(front + back)

        fmt_path: list[str] = []
        for p in self.path:
            if p is PathFill.EXTEND:
                fmt_path.extend(ext)
            else:
                fmt_path.append(next(formatted_it) if p is PathFill.SINGLE else p)
        fmt_sect: list[str] = []
        for p in self.section:
            if p is PathFill.EXTEND:
                fmt_sect.extend(ext)
            else:
                fmt_sect.append(next(formatted_it) if p is PathFill.SINGLE else p)
        return DestWithMount("/".join(fmt_path), tuple(fmt_sect))  # Allow absolute path


@dataclass
class DestWithMount:
    dest: str
    mount: tuple[str, ...]


def parse_path(spec: str) -> PathSpec:
    replacer = {"{*}": PathFill.SINGLE, "{}": PathFill.SINGLE, "{**}": PathFill.EXTEND}
    location, section = spec.rsplit("::", 1) if "::" in spec else (spec, "")
    path_parts: list[str | PathFill] = [replacer.get(loc, loc) for loc in location.split("/")]
    section_parts: list[str | PathFill] = [replacer.get(sect, sect) for sect in section.split(".")] if section else []
    if path_parts.count(PathFill.EXTEND) + section_parts.count(PathFill.EXTEND) > 1:
        raise ValueError(f"""Found more than one "extend" part ({{**}}) in {spec}""")
    return PathSpec(path_parts, section_parts)
