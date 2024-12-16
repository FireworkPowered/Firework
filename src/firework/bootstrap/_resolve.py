from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .service import Service


class RequirementResolveFailed(Exception):
    pass


class DependencyBrokenError(Exception):
    pass


def _build_dependencies_map(services: Iterable[Service]) -> dict[str, tuple[str, ...]]:
    dependencies_map = {}
    for service in services:
        dependencies_map[service.id] = service.dependencies

        for before in service.before:
            dependencies_map[before] = (*dependencies_map.get(before, ()), service.id)

        for after in service.after:
            dependencies_map[service.id] = (*dependencies_map.get(service.id, ()), after)

    return dependencies_map


def resolve_dependencies(
    services: Iterable[Service],
    exclude: Iterable[Service],
    *,
    reverse: bool = False,
) -> list[set[str]]:
    resolved_id: set[str] = {service.id for service in exclude}
    unresolved: set[Service] = set(services)
    result: list[set[str]] = []

    dependencies_map = _build_dependencies_map(services)

    while unresolved:
        layer = {service.id for service in unresolved if resolved_id.issuperset(dependencies_map[service.id])}

        if layer:
            unresolved = {service for service in unresolved if service.id not in layer}

            resolved_id.update(layer)
            result.append(layer)
        else:
            raise RequirementResolveFailed("Failed to resolve requirements")

    if reverse:
        result.reverse()

    return result


def validate_services_removal(existed: Iterable[Service], services_to_remove: Iterable[Service]):
    graph = {service.id: set() for service in existed}

    for service, deps in _build_dependencies_map(existed).items():
        for dep in deps:
            if dep in graph:
                graph[dep].add(service)

    to_remove = {service.id for service in services_to_remove}

    for node in to_remove:
        for dependent in graph.get(node, ()):
            if dependent not in to_remove:
                raise DependencyBrokenError(f"Cannot remove node '{node}' because node '{dependent}' depends on it.")
