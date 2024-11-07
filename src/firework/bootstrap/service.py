from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from firework.util import RequirementResolveFailed as RequirementResolveFailed
from firework.util import resolve_requirements as _resolve_requirements
from firework.util import validate_removal

if TYPE_CHECKING:
    from .context import ServiceContext


class Service:
    id: str

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


def validate_service_removal(existed: Iterable[Service], remove: Iterable[Service]):
    graph = {service.id: set(service.dependencies) for service in existed}
    validate_removal(graph, {service.id for service in remove})
