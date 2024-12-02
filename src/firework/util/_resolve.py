from typing import Iterable


class RequirementResolveFailed(Exception):
    pass


class DependencyBrokenError(Exception):
    pass


def resolve_requirements(
    components: Iterable[tuple[str, tuple[str, ...]]],
    excluded: set[str] | None = None,
    *,
    reverse: bool = False,
) -> list[set[str]]:
    resolved_id: set[str] = excluded or set()
    unresolved: set[tuple[str, tuple[str, ...]]] = set(components)
    result: list[set[str]] = []
    while unresolved:
        layer = {id for id, deps in unresolved if resolved_id.issuperset(deps)}

        if layer:
            # unresolved -= layer
            unresolved = {item for item in unresolved if item[0] not in layer}

            resolved_id.update(layer)
            result.append(layer)
        else:
            raise RequirementResolveFailed("Failed to resolve requirements")

    if reverse:
        result.reverse()
    return result


def validate_removal(graph: dict[str, set[str]], nodes_to_remove: Iterable[str]):
    reverse_graph: dict[str, set[str]] = {node: set() for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in reverse_graph:
                reverse_graph[dep].add(node)

    for node in nodes_to_remove:
        for dependent in reverse_graph.get(node, set()):
            if dependent not in nodes_to_remove:
                raise DependencyBrokenError(f"Cannot remove node '{node}' because node '{dependent}' depends on it.")
