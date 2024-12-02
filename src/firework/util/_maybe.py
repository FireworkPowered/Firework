from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=BaseException)


@dataclass
class Some(Generic[T]):
    value: T


Maybe: TypeAlias = "Some[T] | None"
