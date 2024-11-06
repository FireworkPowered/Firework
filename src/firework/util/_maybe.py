from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E", bound=BaseException)


@dataclass
class Some(Generic[T]):
    value: T


Maybe = Union[Some[T], None]
