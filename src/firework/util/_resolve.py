from typing import Iterable


class RequirementResolveFailed(Exception):
    pass


class DependencyBrokenError(Exception):
    pass


def resolve_requirements(
    components: Iterable[tuple[str, tuple[str, ...]]],
    reverse: bool = False,
    excluded: set[str] | None = None,
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
                raise DependencyBrokenError(
                    f"Cannot remove node '{node}' because node '{dependent}' depends on it."
                )


if __name__ == "__main__":
    components = [
        ("a", ("b", "c")),
        ("b", ("c",)),
        ("c", ()),
        ("d", ("a",)),
    ]
    print(resolve_requirements(components))
    print(resolve_requirements(components, reverse=True))

    try:
        print(resolve_requirements([("a", ("b",)), ("b", ("a",))]))
    except RequirementResolveFailed as e:
        print(e)

    graph = {
        'a': {'b', 'c'},
        'b': {'c'},
        'c': set(),
        'd': {'a'},
        'e': {'d'},
        'f': {'e'},
        'g': {'h'},
        'h': set(),
    }

    try:
        nodes_to_remove = {'a'}
    except DependencyBrokenError as e:
        print(f"移除失败: {e}")

    validate_removal(graph, {'a', 'd', 'e', 'f'})
    validate_removal(graph, {'g', 'h'})