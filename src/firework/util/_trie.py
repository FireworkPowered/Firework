from __future__ import annotations

from typing import Any, Generic, Iterable, TypeVar

from ._maybe import Maybe, Some

T = TypeVar("T")


def _common_prefix_length(s1: str, s2: str) -> int:
    ix = 0
    for ix, (c1, c2) in enumerate(zip(s1, s2, strict=False)):
        if c1 != c2:
            return ix
    return ix + 1


class _RadixTrieNode:
    __slots__ = ["children", "value"]

    def __init__(self):
        self.value: Maybe[Any] = None
        self.children: dict[str, _RadixTrieNode] = {}

    def __repr__(self):
        return f"RadixTrieNode(value={self.value}, children={self.children})"


class RadixTrie(Generic[T]):
    def __init__(self):
        self.root = _RadixTrieNode()

    def set(self, key: str, value: T) -> None:
        node = self.root
        i = 0
        while True:
            for edge, child in node.children.items():
                length = _common_prefix_length(edge, key[i:])
                if length == 0:
                    continue

                if length < len(edge):
                    prefix = edge[:length]
                    suffix = edge[length:]
                    mid_node = _RadixTrieNode()
                    mid_node.children[suffix] = child
                    del node.children[edge]
                    node.children[prefix] = mid_node
                    node = mid_node
                else:
                    node = child

                i += length
                break
            else:
                node.children[key[i:]] = node = _RadixTrieNode()
                node.value = Some(value)
                return

            if i == len(key):
                node.value = Some(value)
                return

    def remove(self, key: str) -> None:
        path: list[tuple[_RadixTrieNode, str]] = []
        node = self.root
        i = 0

        while True:
            found = False
            for edge, child in node.children.items():
                length = _common_prefix_length(edge, key[i:])
                if length == len(edge) and i + length <= len(key):
                    path.append((node, edge))
                    node = child
                    i += length
                    if i == len(key):
                        found = True
                    break
            else:
                return

            if found:
                break

        if node.value is None:
            return

        node.value = None

        for parent, edge in path[::-1]:
            child = parent.children[edge]

            if child.value is None:
                if len(child.children) == 1:
                    (child_edge, grandchild) = next(iter(child.children.items()))
                    del parent.children[edge]
                    parent.children[edge + child_edge] = grandchild
                elif len(child.children) == 0:
                    del parent.children[edge]
            else:
                break

    def longest_prefix_key(self, prefix: str) -> str | None:
        node = self.root
        i = 0
        matched_key = ""
        last_key = ""
        last_value = None
        prefix_len = len(prefix)

        while i < prefix_len:
            found = False
            for edge, child in node.children.items():
                length = _common_prefix_length(edge, prefix[i:])
                if length == 0:
                    continue

                if length < len(edge):
                    matched_key += edge[:length]
                    return last_key if last_value is not None else None

                matched_key += edge
                i += length
                node = child
                if node.value is not None:
                    last_value = node.value
                    last_key = matched_key

                found = True
                break

            if not found:
                break

        if last_value is not None:
            return last_key

        return None

    def keys(self) -> list[str]:
        keys = []
        stack = [(self.root, "")]
        while stack:
            node, prefix = stack.pop()
            if node.value is not None:
                keys.append(prefix)
            for edge, child in node.children.items():
                stack.append((child, prefix + edge))
        return keys

    def values(self) -> list[str]:
        values = []
        stack = [(self.root, "")]
        while stack:
            node, prefix = stack.pop()
            if node.value is not None:
                values.append(node.value)
            for edge, child in node.children.items():
                stack.append((child, prefix + edge))
        return values

    def items(self) -> list[tuple[str, T]]:
        items = []
        stack = [(self.root, "")]
        while stack:
            node, prefix = stack.pop()
            if node.value is not None:
                items.append((prefix, node.value))
            for edge, child in node.children.items():
                stack.append((child, prefix + edge))
        return items

    def update(self, items: Iterable[tuple[str, T]]) -> None:
        for key, value in items:
            self.set(key, value)

    def __contains__(self, key: str) -> bool:
        node = self.root
        i = 0
        prefix_len = len(key)

        while i < prefix_len:
            found = False
            for edge, child in node.children.items():
                length = _common_prefix_length(edge, key[i:])

                if length == len(edge):
                    i += length
                    node = child
                    found = True
                    break

            if not found:
                return False

        return node.value is not None
