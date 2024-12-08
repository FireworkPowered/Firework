from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from firework.util import Maybe, safe_dcls_kw

from .capture import Capture, SimpleCapture
from .receiver import Rx


@dataclass(**safe_dcls_kw(slots=True))
class Fragment:
    name: str
    variadic: bool = False
    default: Maybe[Any] = None
    default_factory: Callable[[], Any] | None = None

    separators: str | None = None
    hybrid_separators: bool = True

    capture: Capture = SimpleCapture()
    receiver: Rx[Any] = Rx()
    validator: Callable[[Any], bool] | None = None
    transformer: Callable[[Any], Any] | None = None


def assert_fragments_order(fragments: Iterable[Fragment]):
    default_exists = False
    variadic_exists = False

    for frag in fragments:
        if variadic_exists:
            raise ValueError("Found fragment after a variadic fragment, which is not allowed.")

        if frag.default is not None:
            default_exists = True
        elif default_exists and not frag.variadic:
            raise ValueError("Found a required fragment after an optional fragment, which is not allowed.")

        if frag.variadic:
            if frag.default is not None:
                raise ValueError("A variadic fragment cannot have a default value.")

            variadic_exists = True
