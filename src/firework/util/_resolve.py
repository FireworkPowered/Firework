from typing import Iterable


class RequirementResolveFailed(Exception):
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
