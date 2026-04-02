"""Tests for match combinators (any, all, some, ratio) and the test_count algorithm."""

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────


class _MockRule:
    """Minimal stand-in for ConstraintRule / MatchRule."""

    def __init__(self, result: bool) -> None:
        self._result = result

    def test(self, view_snapshot) -> bool:
        return self._result


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

    def test_empty_rules_is_droppable(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch().is_droppable(()) is True

    def test_non_empty_rules_not_droppable(self):
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch().is_droppable(_rules(True)) is False

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

    def test_empty_rules_is_droppable(self):
        from plugin.rules.matches.all import AllMatch

        assert AllMatch().is_droppable(()) is True

    def test_name(self):
        from plugin.rules.matches.all import AllMatch

        assert AllMatch.name() == "all"


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

    def test_count_exceeds_rules_is_droppable(self):
        from plugin.rules.matches.some import SomeMatch

        # count=5 but only 3 rules → droppable
        assert SomeMatch(5).is_droppable(_rules(True, True, True)) is True

    def test_valid_count_not_droppable(self):
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch(2).is_droppable(_rules(True, True, True)) is False

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

    def test_zero_denominator_is_droppable(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(1, 0).is_droppable(_rules(True)) is True

    def test_ratio_above_one_is_droppable(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(3, 2).is_droppable(_rules(True)) is True

    def test_valid_ratio_not_droppable(self):
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(2, 3).is_droppable(_rules(True, True, True)) is False

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
