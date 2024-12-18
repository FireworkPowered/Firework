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
) -> list[list[str]]:
    services = list(services)

    # 构建初始依赖图：dependencies + after
    dependencies_map: dict[str, set[str]] = {}
    for s in services:
        deps = set(s.dependencies) | set(s.after)  # after相当于额外依赖
        dependencies_map[s.id] = deps

    # 处理 before 约束：A before B -> B depends on A
    for s in services:
        for b in s.before:
            if b not in dependencies_map:
                dependencies_map[b] = set()
            dependencies_map[b].add(s.id)

    unresolved = {s.id: s for s in services}
    resolved_id = {i.id for i in exclude}
    result: list[list[str]] = []

    while unresolved:
        # 找出所有依赖已解决的候选服务
        layer_candidates = [service for service in unresolved.values() if dependencies_map.get(service.id, set()) <= resolved_id]

        if not layer_candidates:
            raise TypeError("Failed to resolve requirements due to cyclic dependencies or unmet constraints.")

        # 根据是否有 before 约束进行分类
        layer_without_before = [s.id for s in layer_candidates if not s.before]
        layer_with_before = [s.id for s in layer_candidates if s.before]

        # 优先无 before 的服务，一旦无 before 的服务存在，就先放这一层
        if layer_without_before:
            current_layer = layer_without_before
        else:
            current_layer = layer_with_before

        # 从未解决中移除当前层的服务
        for cid in current_layer:
            del unresolved[cid]

        resolved_id.update(current_layer)
        result.append(current_layer)

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
