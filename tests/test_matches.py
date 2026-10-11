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


# ── AnyMatch ──────────────────────────────────────────────────────────────────


class TestAnyMatch:
    def test_one_true_rule_passes(self, make_snapshot):
        from plugin.rules.matches.any import AnyMatch

        snap = make_snapshot()
        assert AnyMatch().test(snap, _rules(False, True, False)) is True

    def test_all_false_fails(self, make_snapshot):
        from plugin.rules.matches.any import AnyMatch

        snap = make_snapshot()
        assert AnyMatch().test(snap, _rules(False, False)) is False

    def test_all_true_passes(self, make_snapshot):
        from plugin.rules.matches.any import AnyMatch

        snap = make_snapshot()
        assert AnyMatch().test(snap, _rules(True, True)) is True

    def test_empty_rules_fails(self, make_snapshot):
        from plugin.rules.matches.any import AnyMatch

        snap = make_snapshot()
        assert AnyMatch().test(snap, ()) is False

    def test_empty_rules_folds_to_false(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch().fold(()).value is False

    def test_non_empty_rules_does_not_fold(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch().fold(_rules(True)).value is None

    def test_name(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.name() == "any"

    def test_can_support(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.can_support("any") is True
        assert AnyMatch.can_support("all") is False


# ── AllMatch ──────────────────────────────────────────────────────────────────


class TestAllMatch:
    def test_all_true_passes(self, make_snapshot):
        from plugin.rules.matches.all import AllMatch

        snap = make_snapshot()
        assert AllMatch().test(snap, _rules(True, True, True)) is True

    def test_one_false_fails(self, make_snapshot):
        from plugin.rules.matches.all import AllMatch

        snap = make_snapshot()
        assert AllMatch().test(snap, _rules(True, False, True)) is False

    def test_all_false_fails(self, make_snapshot):
        from plugin.rules.matches.all import AllMatch

        snap = make_snapshot()
        assert AllMatch().test(snap, _rules(False, False)) is False

    def test_single_true_passes(self, make_snapshot):
        from plugin.rules.matches.all import AllMatch

        snap = make_snapshot()
        assert AllMatch().test(snap, _rules(True)) is True

    def test_empty_rules_passes(self, make_snapshot):
        from plugin.rules.matches.all import AllMatch

        # all() of empty iterable is True in Python
        snap = make_snapshot()
        assert AllMatch().test(snap, ()) is True

    def test_empty_rules_folds_to_true(self):
        """`all([])` is True -- the opposite constant to an empty `any`, and the distinction
        `fold()` exists to carry."""
        from plugin.rules.matches.all import AllMatch

        assert AllMatch().fold(()).value is True

    def test_name(self):
        from plugin.rules.matches.all import AllMatch

        assert AllMatch.name() == "all"


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


# ── SomeMatch ─────────────────────────────────────────────────────────────────


class TestSomeMatch:
    def test_exactly_n_pass(self, make_snapshot):
        from plugin.rules.matches.some import SomeMatch

        snap = make_snapshot()
        assert SomeMatch(2).test(snap, _rules(True, True, False)) is True

    def test_more_than_n_pass(self, make_snapshot):
        from plugin.rules.matches.some import SomeMatch

        snap = make_snapshot()
        assert SomeMatch(2).test(snap, _rules(True, True, True)) is True

    def test_fewer_than_n_fail(self, make_snapshot):
        from plugin.rules.matches.some import SomeMatch

        snap = make_snapshot()
        assert SomeMatch(3).test(snap, _rules(True, True, False)) is False

    def test_zero_count_always_passes(self, make_snapshot):
        from plugin.rules.matches.some import SomeMatch

        snap = make_snapshot()
        assert SomeMatch(0).test(snap, _rules(False, False)) is True

    def test_explicit_zero_count_stored_as_zero(self):
        """Regression: `nth(self.args, 0) or -1` treated explicit 0 as missing, storing -1."""
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch(0).count == 0

    @pytest.mark.parametrize("args", [(), (-1,), ("2",), (True,), (2.5,), (1, 2)])
    def test_invalid_args_are_rejected(self, args):
        """An invalid count used to fall back to "satisfied by nothing", i.e. matching every file."""
        from plugin.rules.matches.some import SomeMatch

        with pytest.raises(ValueError, match='"some"'):
            SomeMatch(*args)

    def test_rule_with_invalid_some_is_not_made(self):
        import plugin.rules.constraints  # ruff:ignore[unused-import]
        from plugin.rules.match import MatchRule
        from plugin.types import StConstraintRule
        from plugin.types import StMatchRule

        rule = MatchRule.make(
            StMatchRule(match="some", rules=[StConstraintRule(constraint="is_extension", args=["py"])])
        )

        assert rule is None

    def test_count_exceeds_rules_folds_to_false(self):
        from plugin.rules.matches.some import SomeMatch

        # count=5 but only 3 rules → droppable
        assert SomeMatch(5).fold(_rules(True, True, True)).value is False

    def test_valid_count_does_not_fold(self):
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch(2).fold(_rules(True, True, True)).value is None

    def test_name(self):
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch.name() == "some"


# ── RatioMatch ────────────────────────────────────────────────────────────────


class TestRatioMatch:
    def test_two_thirds_passes(self, make_snapshot):
        from plugin.rules.matches.ratio import RatioMatch

        # 2/3 ratio → need ceil(2/3 * 3) = 2 passing rules out of 3
        snap = make_snapshot()
        assert RatioMatch(2, 3).test(snap, _rules(True, True, False)) is True

    def test_two_thirds_fails(self, make_snapshot):
        from plugin.rules.matches.ratio import RatioMatch

        snap = make_snapshot()
        assert RatioMatch(2, 3).test(snap, _rules(True, False, False)) is False

    def test_half_passes(self, make_snapshot):
        from plugin.rules.matches.ratio import RatioMatch

        snap = make_snapshot()
        assert RatioMatch(1, 2).test(snap, _rules(True, False)) is True

    def test_full_ratio_all_must_pass(self, make_snapshot):
        from plugin.rules.matches.ratio import RatioMatch

        snap = make_snapshot()
        assert RatioMatch(1, 1).test(snap, _rules(True, True)) is True
        assert RatioMatch(1, 1).test(snap, _rules(True, False)) is False

    def test_zero_numerator_stored_as_zero(self):
        """Regression: `nth(...) or 0` conflated missing with explicit zero."""
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(0, 3).numerator == 0
        assert RatioMatch(2, 4).numerator == 2

    @pytest.mark.parametrize("args", [(), (1,), (1, 0), (-1, 2), (1, -2), ("1", "2"), (True, 2), (1, 2, 3)])
    def test_invalid_args_are_rejected(self, args):
        """An invalid ratio used to fall back to "demands nothing", i.e. matching every file."""
        from plugin.rules.matches.ratio import RatioMatch

        with pytest.raises(ValueError, match='"ratio"'):
            RatioMatch(*args)

    def test_zero_ratio_folds_to_true(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(0, 3).fold(_rules(False, False)).value is True

    @pytest.mark.parametrize(("args", "passing"), [((7, 25), 7), ((0.28, 1), 7), ((14, 50), 7)])
    def test_goal_is_exact(self, make_snapshot, args, passing):
        """`0.28 * 25` is `7.000000000000001` in floats, which `ceil()` turned into a goal of 8."""
        from plugin.rules.matches.ratio import RatioMatch

        rules = _rules(*([True] * passing + [False] * (25 - passing)))

        assert RatioMatch(*args).test(make_snapshot(), rules) is True
        assert RatioMatch(*args).test(make_snapshot(), (*rules[1:], _MockRule(False))) is False

    def test_ratio_above_one_folds_to_false(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(3, 2).fold(_rules(True)).value is False

    def test_valid_ratio_does_not_fold(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(2, 3).fold(_rules(True, True, True)).value is None

    def test_name(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch.name() == "ratio"


# ── AbstractMatch.test_count algorithm ───────────────────────────────────────


class TestTestCount:
    """Direct tests of the test_count short-circuit counting algorithm."""

    @pytest.fixture()
    def snap(self, make_snapshot):
        return make_snapshot()

    def test_goal_zero_always_true(self, snap):
        from plugin.rules.matches.any import AnyMatch

        # test_count is a static method on AbstractMatch
        assert AnyMatch.test_count(snap, _rules(False, False), 0) is True

    def test_exact_goal_met(self, snap):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.test_count(snap, _rules(True, True, False), 2) is True

    def test_goal_not_met(self, snap):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.test_count(snap, _rules(True, False, False), 2) is False

    def test_goal_exceeds_rule_count(self, snap):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.test_count(snap, _rules(True, True), 3) is False

    def test_all_pass(self, snap):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch.test_count(snap, _rules(True, True, True), 3) is True

    def test_early_exit_when_tolerance_exhausted(self, snap):
        """Ensure the algorithm short-circuits rather than evaluating all rules."""
        from plugin.rules.matches.any import AnyMatch

        call_count = 0

        class CountingRule:
            def __init__(self, result: bool) -> None:
                self._result = result

            def test(self, _) -> bool:
                nonlocal call_count
                call_count += 1
                return self._result

        # goal=3, tolerance=5-3=2
        # Rules: [F, F, F, T, T]
        # After rule[2] fails: tolerance drops to -1
        # rule[3] check: tolerance < 0 → bail without calling rule[3] or rule[4]
        rules = tuple(CountingRule(r) for r in [False, False, False, True, True])
        result = AnyMatch.test_count(snap, rules, 3)
        assert result is False
        # Only rules 0,1,2 evaluated (3 calls), not 3 or 4
        assert call_count == 3
