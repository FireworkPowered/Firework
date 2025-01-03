from __future__ import annotations

import pytest
from elaina_segment import Buffer

from firework.framework.command.core import Fragment, SubcommandPattern
from firework.framework.command.core.analyzer import LoopflowRejectReason

from .asserts import analyze


def test_aliases():
    pat = SubcommandPattern.build("test").option(
        "name",
        Fragment("name"),
        aliases=["--name"],
    )

    a, sn, bf = analyze(pat, Buffer(["test --name hello"]))
    a.expect_completed()
    sn.expect_determined()

    pat = SubcommandPattern.build("test")
    pat.subcommand("sub", aliases=["subcmd"])

    a, sn, bf = analyze(pat, Buffer(["test subcmd"]))
    a.expect_completed()
    sn.expect_determined()


def test_add_option():
    pat = SubcommandPattern.build("test")
    pat.option("name", Fragment("name"), hybrid_separators=True, aliases=["--name"], header_separators="=")

    a, sn, bf = analyze(pat, Buffer(["test --name hello"]))
    a.expect_completed()
    sn.expect_determined()

    # no hybrid separators
    pat = SubcommandPattern.build("test", separators="|")
    pat.option("name", Fragment("name"), aliases=["--name"], header_separators="=", hybrid_separators=False)

    a, sn, bf = analyze(pat, Buffer(["test|--name=hello"]))
    a.expect_completed()

    a, sn, bf = analyze(pat, Buffer(["test|--name hello"]))
    a.expect(LoopflowRejectReason.unexpected_segment)

    pat = SubcommandPattern.build("test", separators="|")
    pat.option("name", Fragment("name"), Fragment("aaa"), aliases=["--name"], separators=",", hybrid_separators=True)

    a, sn, bf = analyze(pat, Buffer(["test|--name|hello,aaa"]))
    a.expect_completed()

    a, sn, bf = analyze(pat, Buffer(["test|--name|hello|aaa"]))
    a.expect_completed()

    with pytest.raises(ValueError, match="header_separators must be used with fragments"):
        pat = SubcommandPattern.build("test", separators="|")
        pat.option("name", aliases=["--name"], header_separators="=")
