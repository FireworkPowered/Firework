from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Concatenate, Generator, Generic, Literal, Self, TypeVar, overload

from .globals import COLLECTING_CONTEXT_VAR, GLOBAL_COLLECT_CONTEXT
from .implement import FeatureImpl
from .record import CollectSignal, FeatureEndpointLabel
from .selection import Candidates
from .typing import CQ, P1, P2, C, P, R, T

if TYPE_CHECKING:
    from .context import CollectContext

CollectEndpointTarget = Generator[CollectSignal, None, T]


def _ensure_entity(func: Callable) -> FeatureImpl:
    if hasattr(func, "__flywheel_implement_entity__"):
        entity: FeatureImpl = func.__flywheel_implement_entity__  # type: ignore[reportFunctionMemberAccess]
    else:
        entity = FeatureImpl(func)
        func.__flywheel_implement_entity__ = entity  # type: ignore[reportFunctionMemberAccess]

    return entity


class ImplementSide(Generic[P, CQ]):
    collector: Callable[P, CollectEndpointTarget]

    @overload
    def __init__(self: ImplementSide[P1, Callable[P2, R]], target: Callable[P1, CollectEndpointTarget[Callable[P2, R]]]): ...
    @overload
    def __init__(self: ImplementSide[P1, Callable], target: Callable[P1, CollectEndpointTarget[Any]]): ...
    def __init__(self, target):
        self.collector = target

    def impl(self: ImplementSide[P1, C], entrypoint: Feature, *args: P1.args, **kwargs: P1.kwargs):
        def wrapper(callee: C) -> C:
            entity = _ensure_entity(callee)
            entity.add_target(entrypoint, self.collector(*args, **kwargs))
            return callee

        return wrapper


class BoundImplementSide(ImplementSide[P, CQ]):
    def impl(self: BoundImplementSide[Concatenate[T, P], C], entrypoint: BoundedFeature[Any, T], *args: P.args, **kwargs: P.kwargs):
        def wrapper(callee: C) -> C:
            entity = _ensure_entity(callee)
            entity.add_target(entrypoint, self.collector(entrypoint.instance, *args, **kwargs))
            return callee

        return wrapper


class CallSide(Generic[C]):
    def __init__(self, callee: C):
        self.callee = callee


class BoundCallSide(CallSide[C]): ...


ImplementSideT = TypeVar("ImplementSideT", bound=ImplementSide)
CallSideT = TypeVar("CallSideT", bound=CallSide)


@dataclass(init=False, eq=True, unsafe_hash=True)
class Feature(Generic[ImplementSideT]):
    implement_side: ImplementSideT

    def __init__(self, implement_side: ImplementSideT):
        self.implement_side = implement_side

    @overload
    @classmethod
    def static(cls, func: Callable[P1, CollectEndpointTarget[Callable[P2, R]]]) -> Feature[ImplementSide[P1, Callable[P2, R]]]: ...
    @overload
    @classmethod
    def static(cls, func: Callable[P1, CollectEndpointTarget[Any]]) -> Feature[ImplementSide[P1, Callable]]: ...
    @classmethod
    def static(cls, func) -> Feature[ImplementSide]:
        return cls(ImplementSide(func))  # type: ignore

    @overload
    @classmethod
    def method(
        cls, func: Callable[P1, CollectEndpointTarget[Callable[P2, R]]]
    ) -> Feature[BoundImplementSide[P1, Callable[P2, R]]]: ...
    @overload
    @classmethod
    def method(cls, func: Callable[P1, CollectEndpointTarget[Any]]) -> Feature[BoundImplementSide[P1, Callable]]: ...
    @classmethod
    def method(cls, func) -> Feature[BoundImplementSide]:
        return cls(BoundImplementSide(func))  # type: ignore

    @property
    def signature(self):
        return FeatureEndpointLabel(self)

    @overload
    def select(self: Feature[ImplementSide[..., C]], *, expect_complete: bool = True) -> Candidates[C]: ...
    @overload
    def select(self: Feature[BoundImplementSide[..., C]], *, expect_complete: bool = True) -> Candidates[C]: ...
    def select(self, *, expect_complete: bool = True) -> Candidates:
        return Candidates(self, expect_complete)

    def impl(self: Feature[ImplementSide[P1, C]], *args: P1.args, **kwargs: P1.kwargs):
        return self.implement_side.impl(self, *args, **kwargs)

    def _call(self, call_side: CallSideT) -> CallableFeature[ImplementSideT, CallSideT]:
        return CallableFeature(self.implement_side, call_side)

    def call_static(self, func: C) -> CallableFeature[ImplementSideT, CallSide[C]]:
        return self._call(CallSide(func))

    def call_method(self, func: C) -> CallableFeature[ImplementSideT, BoundCallSide[C]]:
        return self._call(BoundCallSide(func))

    @overload
    def __get__(self, instance: None, owner: Any = None, /) -> Self: ...
    @overload
    def __get__(self, instance: T, owner: Any = None, /) -> BoundedFeature[ImplementSideT, T]: ...
    def __get__(self, instance: Any, owner: Any = None, /):
        if instance is None:
            return self

        return BoundedFeature(self.implement_side, instance, owner)


@dataclass(init=False, eq=True, unsafe_hash=True)
class CallableFeature(Generic[ImplementSideT, CallSideT], Feature[ImplementSideT]):
    call_side: CallSideT

    def __init__(self, implement_side: ImplementSideT, call_side: CallSideT):
        super().__init__(implement_side)
        self.call_side = call_side

    @overload
    def __get__(self, instance: None, owner: Any = None, /) -> Self: ...
    @overload
    def __get__(self, instance: T, owner: Any = None, /) -> BoundedCallableFeature[ImplementSideT, CallSideT, T]: ...
    def __get__(self, instance: Any, owner: Any = None, /):
        if instance is None:
            return self

        return BoundedCallableFeature(self.implement_side, self.call_side, instance, owner)

    @overload
    def __call__(self: CallableFeature[Any, BoundCallSide[Callable[P, R]]], *args: P.args, **kwargs: P.kwargs) -> R: ...
    @overload
    def __call__(self: CallableFeature[Any, CallSide[Callable[P, R]]], *args: P.args, **kwargs: P.kwargs) -> R: ...
    def __call__(self, *args, **kwargs):
        return self.call_side.callee(*args, **kwargs)


@dataclass(init=False, eq=True, unsafe_hash=True)
class BoundedFeature(Generic[ImplementSideT, T], Feature[ImplementSideT]):
    instance: T = field(hash=False)
    owner: type = field(hash=False)

    @property
    def signature(self):
        if self.instance is not None:
            raise RuntimeError("entrypoint bounded on instance does not support signature")

    def __init__(self, implement_side: ImplementSideT, instance: T, owner: type):
        super().__init__(implement_side)
        self.instance = instance
        self.owner = owner

    @overload
    def impl(
        self: BoundedFeature[BoundImplementSide[Concatenate[T, P1], C], T], *args: P1.args, **kwargs: P1.kwargs
    ) -> Callable[[C], C]: ...
    @overload
    def impl(self: BoundedFeature[ImplementSide[P1, C], Any], *args: P1.args, **kwargs: P1.kwargs) -> Callable[[C], C]: ...
    def impl(self, *args, **kwargs) -> Callable[[C], C]:
        return self.implement_side.impl(self, *args, **kwargs)


@dataclass(init=False, eq=True, unsafe_hash=True)
class BoundedCallableFeature(
    Generic[ImplementSideT, CallSideT, T],
    CallableFeature[ImplementSideT, CallSideT],
    BoundedFeature[ImplementSideT, T],
):
    instance: T = field(hash=False)
    owner: type = field(hash=False)

    def __init__(self, implement_side: ImplementSideT, call_side: CallSideT, instance: T, owner: type):
        super().__init__(implement_side, call_side)
        self.instance = instance
        self.owner = owner

    @overload
    def __call__(
        self: BoundedCallableFeature[Any, BoundCallSide[Callable[Concatenate[T, P], R]], T], *args: P.args, **kwargs: P.kwargs
    ) -> R: ...
    @overload
    def __call__(self: BoundedCallableFeature[Any, CallSide[Callable[P, R]], Any], *args: P.args, **kwargs: P.kwargs) -> R: ...
    def __call__(self, *args, **kwargs):
        if isinstance(self.call_side, BoundCallSide):
            return self.call_side.callee(self.instance, *args, **kwargs)

        return self.call_side.callee(*args, **kwargs)


def feature_collect(target: Literal["local", "global"] | CollectContext = "local"):
    if target == "local":
        context = COLLECTING_CONTEXT_VAR.get()
    elif target == "global":
        context = GLOBAL_COLLECT_CONTEXT
    else:
        context = target

    def wrapper(func: C) -> C:
        # entity = _ensure_entity(func
        if not hasattr(func, "__flywheel_implement_entity__"):
            raise RuntimeError("[@]feature_collect must be used with [@]feature.impl")

        entity = func.__flywheel_implement_entity__  # type: ignore
        context.collect(entity)
        return func

    return wrapper
