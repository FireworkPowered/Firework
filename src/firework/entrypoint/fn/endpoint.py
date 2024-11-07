from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generator, Generic, Protocol, overload

from ..typing import CQ, P1, P2, C, CnR, P, R, T
from .implement import FnImplementEntity
from .record import CollectSignal, FnRecordLabel
from .selection import Candidates

if TYPE_CHECKING:
    pass

CollectEndpointTarget = Generator[CollectSignal, None, T]


class Collectee(Protocol[CnR]):
    @overload
    def __call__(self: Collectee[None], entity: C) -> FnImplementEntity[C]: ...
    @overload
    def __call__(self: Collectee[C], entity: FnImplementEntity[C]) -> FnImplementEntity[C]: ...
    @overload
    def __call__(self: Collectee[C], entity: C) -> FnImplementEntity[C]: ...


@dataclass(init=False, eq=True, unsafe_hash=True)
class Fn(Generic[P, CQ]):
    target: Callable[P, CollectEndpointTarget]

    @overload
    def __init__(self: Fn[P1, Callable[P2, R]], target: Callable[P1, CollectEndpointTarget[Callable[P2, R]]]): ...

    @overload
    def __init__(self: Fn[P1, Callable], target: Callable[P1, CollectEndpointTarget[Any]]): ...

    def __init__(self, target):
        self.target = target

    @property
    def signature(self):
        return FnRecordLabel(self)

    def route(self: Fn[P1, CQ], *args: P1.args, **kwargs: P1.kwargs) -> Collectee[CQ]:
        def wrapper(entity: C | FnImplementEntity[C]) -> FnImplementEntity[C]:
            if not isinstance(entity, FnImplementEntity):
                entity = FnImplementEntity(entity)

            entity.add_target(self, self.target(*args, **kwargs))
            return entity

        return wrapper  # type: ignore

    def select(self: Fn[..., C], expect_complete: bool = True) -> Candidates[C]:
        return Candidates(self, expect_complete)

    def call(self, callee: C) -> C:
        # TODO
        ...


# @overload
# def wrap_endpoint(
#     target: Callable[P1, CollectEndpointTarget[Callable[P2, R]]],
# ) -> FnCollectDescriptor[P1, Callable[P2, R]]: ...
# @overload
# def wrap_endpoint(target: Callable[P1, CollectEndpointTarget[Any]]) -> FnCollectDescriptor[P1, Callable]: ...
# def wrap_endpoint(target):
#     return FnCollectEndpoint(target).descriptor
