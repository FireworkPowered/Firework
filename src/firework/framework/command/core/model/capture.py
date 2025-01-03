from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from elaina_segment import Quoted, UnmatchedQuoted
from typing_extensions import TypeAlias

from firework.util import Maybe, Some, safe_dcls_kw

from ..err import RegexMismatch, UnexpectedType

if TYPE_CHECKING:
    from elaina_segment.buffer import AheadToken, Buffer, SegmentToken

T = TypeVar("T")

CaptureResult: TypeAlias = "tuple[T, Maybe[Any], SegmentToken[T] | AheadToken[T]]"


class Capture(Generic[T]):
    def capture(self, buffer: Buffer[Any], separators: str) -> CaptureResult[T]: ...


class SimpleCapture(Capture[Any]):
    def capture(self, buffer: Buffer[Any], separators: str) -> CaptureResult[Any]:
        token = buffer.next(separators)
        return token.val, None, token


@dataclass(**safe_dcls_kw(eq=True, unsafe_hash=True, slots=True))
class ObjectCapture(Capture[T]):
    type: type[T] | tuple[type[T], ...]

    def capture(self, buffer: Buffer[Any], separators: str) -> CaptureResult[T]:
        token = buffer.next(separators)
        if not isinstance(token.val, self.type):
            raise UnexpectedType(self.type, type(token.val))

        return token.val, None, token


Plain: TypeAlias = "str | Quoted[str] | UnmatchedQuoted[str]"


@dataclass(**safe_dcls_kw(eq=True, unsafe_hash=True, slots=True))
class PlainCapture(Capture[Plain]):
    def capture(self, buffer: Buffer[Any], separators: str) -> CaptureResult[Plain]:
        token = buffer.next(separators)

        if isinstance(token.val, str):
            return token.val, None, token
        if isinstance(token.val, (Quoted, UnmatchedQuoted)):
            if isinstance(token.val.ref, str):
                val = token.val.ref
            elif next((i for i in token.val.ref if not isinstance(i, str)), None) is None:
                val = "".join(token.val.ref)
            else:
                raise UnexpectedType(str, type(next(i for i in token.val.ref if not isinstance(i, str))))

            return val, None, token
        raise UnexpectedType(str, type(token.val))


@dataclass(**safe_dcls_kw(eq=True, unsafe_hash=True, slots=True))
class RegexCapture(Capture[re.Match[str]]):
    pattern: str | re.Pattern[str]
    match_quote: bool = False

    def capture(self, buffer: Buffer[Any], separators: str) -> CaptureResult[re.Match[str]]:
        token = buffer.next(separators)

        if isinstance(token.val, str):
            val = token.val
        elif isinstance(token.val, (Quoted, UnmatchedQuoted)) and self.match_quote:
            if isinstance(token.val.ref, str):
                val = token.val.ref
            elif next((i for i in token.val.ref if not isinstance(i, str)), None) is None:
                val = "".join(token.val.ref)
            else:
                raise UnexpectedType(str, type(next(i for i in token.val.ref if not isinstance(i, str))))
        else:
            raise UnexpectedType(str, token.val)

        match = re.match(self.pattern, val)
        if not match:
            raise RegexMismatch(self.pattern, val)

        last = match.string[match.end() :]
        if last:
            return match, Some(last), token

        return match, None, token
