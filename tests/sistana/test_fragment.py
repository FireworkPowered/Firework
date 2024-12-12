import pytest

from firework.framework.command.core.model.fragment import Fragment, assert_fragments_order
from firework.util import Some


def test_assert_fragments_order_valid():
    fragments = [Fragment(name="frag1"), Fragment(name="frag2", default=Some("default")), Fragment(name="frag3", variadic=True)]
    assert_fragments_order(fragments)


def test_assert_fragments_order_required_after_optional():
    fragments = [Fragment(name="frag1", default=Some("default")), Fragment(name="frag2")]
    with pytest.raises(ValueError, match="Found a required fragment after an optional fragment, which is not allowed."):
        assert_fragments_order(fragments)


def test_assert_fragments_order_variadic_with_default():
    fragments = [Fragment(name="frag1", variadic=True, default=Some("default"))]
    with pytest.raises(ValueError, match="A variadic fragment cannot have a default value."):
        assert_fragments_order(fragments)


def test_assert_fragments_order_fragment_after_variadic():
    fragments = [Fragment(name="frag1", variadic=True), Fragment(name="frag2")]
    with pytest.raises(ValueError, match="Found fragment after a variadic fragment, which is not allowed."):
        assert_fragments_order(fragments)


# def test_nepattern():
#     from nepattern import WIDE_BOOLEAN

#     pat = SubcommandPattern.build("test")

#     pat.option("--foo", Fragment("foo", type=Some(int)))
#     pat.option("--bar", Fragment("bar", type=Some(float)))
#     pat.option("--baz", Fragment("baz", type=Some(bool)))
#     pat.option("--qux", Fragment("qux").apply_nepattern(WIDE_BOOLEAN))

#     a, sn, bf = analyze(pat, Buffer(["test --foo 123 --bar 123.456 --baz true --qux yes"]))
#     a.expect_completed()
#     sn.expect_determined()

#     frag = sn.mix[("test",), "--foo"]["foo"]
#     frag.expect_assigned()
#     frag.expect_value(123)

#     frag = sn.mix[("test",), "--bar"]["bar"]
#     frag.expect_assigned()
#     frag.expect_value(123.456)

#     frag = sn.mix[("test",), "--baz"]["baz"]
#     frag.expect_assigned()
#     frag.expect_value(True)

#     frag = sn.mix[("test",), "--qux"]["qux"]
#     frag.expect_assigned()
#     frag.expect_value(True)
