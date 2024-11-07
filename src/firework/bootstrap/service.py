from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Iterable

from firework.util import RequirementResolveFailed as RequirementResolveFailed
from firework.util import resolve_requirements as _resolve_requirements

if TYPE_CHECKING:
    from .context import ServiceContext


@dataclass
class Service:
    id: ClassVar[str]

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ()

    async def launch(self, context: ServiceContext):
        async with context.prepare():
            pass

        async with context.online():
            pass

        async with context.cleanup():
            pass


def resolve_services_dependency(services: Iterable[Service], reverse: bool = False, exclude: Iterable[str] | None = None):
    return _resolve_requirements(
        [(service.id, service.dependencies) for service in services],
        reverse=reverse,
        excluded=set(exclude) if exclude else None,
    )
