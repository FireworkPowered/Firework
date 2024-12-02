from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from typing_extensions import final

from .record import CollectSignal, EntrypointRecord

TOverload = TypeVar("TOverload", bound="OverloadSpec", covariant=True)
TCallValue = TypeVar("TCallValue")
TCollectValue = TypeVar("TCollectValue")
TSignature = TypeVar("TSignature")


class OverloadSpec(Generic[TSignature, TCollectValue, TCallValue]):
    def __init__(self, name: str) -> None:
        self.name = name

    @final
    def hold(self, value: TCollectValue):
        return CollectSignal(self, value)

    @final
    def dig(self, record: EntrypointRecord, call_value: TCallValue, *, name: str | None = None) -> dict[Callable, None]:
        name = name or self.name
        if name not in record.scopes:
            raise NotImplementedError("cannot lookup any implementation with given arguments")

        return self.harvest(record.scopes[name], call_value)

    @final
    def lay(self, record: EntrypointRecord, collect_value: TCollectValue, implement: Callable, *, name: str | None = None):
        name = name or self.name
        if name not in record.scopes:
            record.scopes[name] = {}

        collection = self.collect(record.scopes[name], self.digest(collect_value))
        collection[implement] = None

    def digest(self, collect_value: TCollectValue) -> TSignature:
        raise NotImplementedError

    def collect(self, scope: dict, signature: TSignature) -> dict[Callable, None]:
        raise NotImplementedError

    def harvest(self, scope: dict, call_value: TCallValue) -> dict[Callable, None]:
        raise NotImplementedError

    def access(self, scope: dict, signature: TSignature) -> dict[Callable, None] | None:
        raise NotImplementedError


@dataclass(eq=True, frozen=True)
class SimpleOverloadSignature:
    value: Any


class SimpleOverload(OverloadSpec[SimpleOverloadSignature, Any, Any]):
    def digest(self, collect_value: Any) -> SimpleOverloadSignature:
        return SimpleOverloadSignature(collect_value)

    def collect(self, scope: dict, signature: SimpleOverloadSignature) -> dict[Callable, None]:
        if signature.value not in scope:
            target = scope[signature.value] = {}
        else:
            target = scope[signature.value]

        return target

    def harvest(self, scope: dict, call_value: Any) -> dict[Callable, None]:
        if call_value in scope:
            return scope[call_value]

        return {}

    def access(self, scope: dict, signature: SimpleOverloadSignature) -> dict[Callable, None] | None:
        if signature.value in scope:
            return scope[signature.value]


@dataclass(eq=True, frozen=True)
class TypeOverloadSignature:
    type: type[Any]


class TypeOverload(OverloadSpec[TypeOverloadSignature, "type[Any]", Any]):
    def digest(self, collect_value: type) -> TypeOverloadSignature:
        return TypeOverloadSignature(collect_value)

    def collect(self, scope: dict, signature: TypeOverloadSignature) -> dict[Callable, None]:
        if signature.type not in scope:
            target = scope[signature.type] = {}
        else:
            target = scope[signature.type]

        return target

    def harvest(self, scope: dict, call_value: Any) -> dict[Callable, None]:
        t = type(call_value)
        if t in scope:
            return scope[t]

        return {}

    def access(self, scope: dict, signature: TypeOverloadSignature) -> dict[Callable, None] | None:
        if signature.type in scope:
            return scope[signature.type]


class _SingletonOverloadSignature: ...


SINGLETON_SIGN = _SingletonOverloadSignature()


class SingletonOverload(OverloadSpec[_SingletonOverloadSignature, None, None]):
    SIGNATURE = SINGLETON_SIGN

    def digest(self, collect_value) -> _SingletonOverloadSignature:  # noqa: ARG002
        return SINGLETON_SIGN

    def collect(self, scope: dict, signature) -> dict[Callable, None]:  # noqa: ARG002
        s = scope[None] = {}
        return s

    def harvest(self, scope: dict, call_value) -> dict[Callable, None]:  # noqa: ARG002
        return scope[None]

    def access(self, scope: dict, signature) -> dict[Callable, None] | None:  # noqa: ARG002
        if None in scope:
            return scope[None]


SINGLETON_OVERLOAD = SingletonOverload("singleton")
