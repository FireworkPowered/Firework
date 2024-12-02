"""
This module handles whitespaces and comments
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lark.lark import Lark
from lark.visitors import Transformer, v_args

from .types import WSC, BlockStyleComment, LineStyleComment, WhiteSpace

if TYPE_CHECKING:
    from lark.lexer import Token


class WSCTransformer(Transformer):
    """
    A [Transformer][lark.visitors.Transformer] handling whitespaces and comments.
    """

    @v_args(inline=True)
    def WS(self, token: Token) -> WhiteSpace:  # noqa: N802
        return WhiteSpace(token.value)

    def CPP_COMMENT(self, token: Token) -> LineStyleComment:  # noqa: N802
        return LineStyleComment(token.value[2:])

    def C_COMMENT(self, token: Token) -> BlockStyleComment:  # noqa: N802
        return BlockStyleComment(token.value[2:-2])

    def wscs(self, wscs: list[WSC]) -> list[WSC]:
        return wscs


transformer = WSCTransformer()


def encode_wsc(wsc: WSC):
    """
    Encode a [WSC][kayaku.backend.types.WSC] into its string representation.

    :param wsc: The Whitespace or Comment to encode.
    """
    if isinstance(wsc, LineStyleComment):
        return f"//{wsc}"
    if isinstance(wsc, BlockStyleComment):
        return f"/*{wsc}*/"
    if isinstance(wsc, WhiteSpace):
        return str(wsc)
    raise NotImplementedError(f"Unknown whitespace or comment type: {wsc!r}")


parser = Lark.open(
    "grammar/wsc.lark",
    rel_to=__file__,
    lexer="basic",
    parser="lalr",
    start="wscs",
    maybe_placeholders=False,
    regex=True,
    transformer=transformer,
)
