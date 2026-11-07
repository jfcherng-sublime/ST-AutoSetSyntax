"""Tests for match combinators (any, all, some, ratio) and the test_count algorithm."""

import pytest

from plugin.types import UNFOLDED
from plugin.types import Fold

# ── Helpers ───────────────────────────────────────────────────────────────────


class _MockRule:
    """Minimal stand-in for ConstraintRule / MatchRule: depends on the view, so never folds."""

    def __init__(self, result: bool) -> None:
        self._result = result

    def test(self, view_snapshot) -> bool:
        return self._result

    def fold(self) -> Fold:
        return UNFOLDED


class _FoldedRule(_MockRule):
    """A child whose own arguments already settle its result."""

    def __init__(self, value: bool, reason: str) -> None:
        super().__init__(value)
        self._fold = Fold(value, reason)

    def fold(self) -> Fold:
        return self._fold


def _rules(*results: bool) -> tuple[_MockRule, ...]:
    return tuple(_MockRule(r) for r in results)


@pytest.mark.parametrize("match_cls_path", ["any.AnyMatch", "all.AllMatch", "some.SomeMatch", "ratio.RatioMatch"])
def test_match_name_is_derived_from_the_class_name(match_cls_path):
    import importlib

    module, cls_name = match_cls_path.split(".")
    cls = getattr(importlib.import_module(f"plugin.rules.matches.{module}"), cls_name)
    assert cls.name() == module
    assert cls.can_support(module) is True


def _match(path):
    import importlib

    module, cls_name = path.split(".")
    return getattr(importlib.import_module(f"plugin.rules.matches.{module}"), cls_name)


@pytest.mark.parametrize(
    ("match_path", "args", "results", "expected"),
    [
        ("any.AnyMatch", (), (False, True, False), True),
        ("any.AnyMatch", (), (True, True), True),
        ("any.AnyMatch", (), (False, False), False),
        ("any.AnyMatch", (), (), False),
        ("all.AllMatch", (), (True, True, True), True),
        ("all.AllMatch", (), (True, False, True), False),
        ("all.AllMatch", (), (False, False), False),
        ("all.AllMatch", (), (True,), True),
        ("all.AllMatch", (), (), True),
        ("some.SomeMatch", (2,), (True, True, False), True),
        ("some.SomeMatch", (2,), (True, True, True), True),
        ("some.SomeMatch", (3,), (True, True, False), False),
        ("some.SomeMatch", (0,), (False, False), True),
        ("ratio.RatioMatch", (2, 3), (True, True, False), True),
        ("ratio.RatioMatch", (2, 3), (True, False, False), False),
        ("ratio.RatioMatch", (1, 2), (True, False), True),
        ("ratio.RatioMatch", (1, 1), (True, True), True),
        ("ratio.RatioMatch", (1, 1), (True, False), False),
        # Regression: `nth(...) or 0` conflated a missing numerator with an explicit zero.
        ("ratio.RatioMatch", (0, 3), (False, False, False), True),
    ],
)
def test_match_verdict(make_snapshot, match_path, args, results, expected):
    assert _match(match_path)(*args).test(make_snapshot(), _rules(*results)) is expected


@pytest.mark.parametrize(
    ("match_path", "args", "results", "expected"),
    [
        ("any.AnyMatch", (), (), False),
        ("any.AnyMatch", (), (True,), None),
        ("all.AllMatch", (), (), True),  # `all([])` is True: the opposite constant to an empty `any`
        ("some.SomeMatch", (5,), (True, True, True), False),  # count exceeds the rules
        ("some.SomeMatch", (2,), (True, True, True), None),
        ("ratio.RatioMatch", (0, 3), (False, False), True),
        ("ratio.RatioMatch", (3, 2), (True,), False),  # ratio above one
        ("ratio.RatioMatch", (2, 3), (True, True, True), None),
    ],
)
def test_match_fold(match_path, args, results, expected):
    assert _match(match_path)(*args).fold(_rules(*results)).value is expected


# ── Absorbing children ────────────────────────────────────────────────────────


class TestAbsorbingChildSettlesTheMatch:
    """`False` absorbs an `all` and `True` absorbs an `any`: one such child settles the whole match,
    so it must fold -- otherwise a rule that can never (or always) match isn't reported."""

    def test_all_with_a_never_matching_child_never_matches(self):
        from plugin.rules.matches.all import AllMatch

        fold = AllMatch().fold((_MockRule(True), _FoldedRule(False, "no extension was given")))

        assert fold.value is False
        assert fold.reason.endswith("no extension was given")

    def test_any_with_an_always_matching_child_always_matches(self):
        from plugin.rules.matches.any import AnyMatch

        fold = AnyMatch().fold((_MockRule(False), _FoldedRule(True, 'a "threshold" of 0 is met')))

        assert fold.value is True
        assert fold.reason.endswith('a "threshold" of 0 is met')

    def test_identity_children_leave_the_match_depending_on_the_view(self):
        from plugin.rules.matches.all import AllMatch
        from plugin.rules.matches.any import AnyMatch

        assert AllMatch().fold((_MockRule(True), _FoldedRule(True, "x"))) == UNFOLDED
        assert AnyMatch().fold((_MockRule(True), _FoldedRule(False, "x"))) == UNFOLDED

    def test_rule_that_can_never_match_is_reported_as_dropped(self):
        import sublime

        import plugin.rules.constraints  # ruff:ignore[unused-import]
        from plugin.rules import SyntaxRuleCollection
        from plugin.rules.syntax import SyntaxRule
        from plugin.types import DroppedRule
        from plugin.types import StConstraintRule
        from plugin.types import StSyntaxRule

        syntax_rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["Python"],
                match="all",
                rules=[
                    StConstraintRule(constraint="is_extension"),
                    StConstraintRule(constraint="is_extension", args=["py"]),
                ],
            )
        )
        syntax_rule.syntax = sublime.Syntax(name="Python")  # the test stubs resolve no syntax
        collection = SyntaxRuleCollection(rules=(syntax_rule,))

        reasons = [dropped.reason for dropped in map(DroppedRule.make, collection.optimize())]

        assert len(collection) == 0
        assert any(reason.startswith("never matches") and "no extension was given" in reason for reason in reasons)


# ── SomeMatch / RatioMatch arguments ──────────────────────────────────────────


@pytest.mark.parametrize("args", [(), (-1,), ("2",), (True,), (2.5,), (1, 2)])
def test_some_invalid_args_are_rejected(args):
    """An invalid count used to fall back to "satisfied by nothing", i.e. matching every file."""
    from plugin.rules.matches.some import SomeMatch

    with pytest.raises(ValueError, match='"some"'):
        SomeMatch(*args)


def test_rule_with_invalid_some_is_not_made():
    import plugin.rules.constraints  # ruff:ignore[unused-import]
    from plugin.rules.match import MatchRule
    from plugin.types import StConstraintRule
    from plugin.types import StMatchRule

    rule = MatchRule.make(StMatchRule(match="some", rules=[StConstraintRule(constraint="is_extension", args=["py"])]))

    assert rule is None


@pytest.mark.parametrize("args", [(), (1,), (1, 0), (-1, 2), (1, -2), ("1", "2"), (True, 2), (1, 2, 3)])
def test_ratio_invalid_args_are_rejected(args):
    """An invalid ratio used to fall back to "demands nothing", i.e. matching every file."""
    from plugin.rules.matches.ratio import RatioMatch

    with pytest.raises(ValueError, match='"ratio"'):
        RatioMatch(*args)


@pytest.mark.parametrize(("args", "passing"), [((7, 25), 7), ((0.28, 1), 7), ((14, 50), 7)])
def test_ratio_goal_is_exact(make_snapshot, args, passing):
    """`0.28 * 25` is `7.000000000000001` in floats, which `ceil()` turned into a goal of 8."""
    from plugin.rules.matches.ratio import RatioMatch

    rules = _rules(*([True] * passing + [False] * (25 - passing)))

    assert RatioMatch(*args).test(make_snapshot(), rules) is True
    assert RatioMatch(*args).test(make_snapshot(), (*rules[1:], _MockRule(False))) is False
