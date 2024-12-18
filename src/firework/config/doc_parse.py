from __future__ import annotations

import ast
import inspect
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from loguru import logger

if TYPE_CHECKING:
    from dataclasses import Field


def cleanup_src(src: str) -> str:
    lines = src.expandtabs().split("\n")
    margin = len(lines[0]) - len(lines[0].lstrip())
    for i in range(len(lines)):
        lines[i] = lines[i][margin:]
    return "\n".join(lines)


def store_field_description(cls: type, fields: dict[str, Field]) -> None:
    try:
        node = cast(ast.ClassDef, ast.parse(cleanup_src(inspect.getsource(cls))).body[0])
    except (TypeError, OSError):  # NOTE: for REPL.
        logger.error(f"Unable to store description for {cls.__qualname__}, maybe the source file is not reachable.")
        return
    for i, stmt in enumerate(node.body):
        name: str | None = None
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
        if (
            name in fields
            and i + 1 < len(node.body)
            and isinstance((doc_expr := node.body[i + 1]), ast.Expr)
            and isinstance((doc_const := doc_expr.value), ast.Constant)
            and isinstance(doc_string := doc_const.value, str)
            and "description" not in (field := fields[name]).metadata
        ):
            field.metadata = MappingProxyType({**field.metadata.copy(), "description": inspect.cleandoc(doc_string)})
