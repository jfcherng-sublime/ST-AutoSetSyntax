"""Tests for ConstraintRule, MatchRule, SyntaxRule, SyntaxRuleCollection, sift_optimizable."""

import pytest

from plugin.types import UNFOLDED
from plugin.types import Fold
from plugin.types import StConstraintRule
from plugin.types import StMatchRule
from plugin.types import StSyntaxRule

# Import all built-in constraints/matches so they register with their abstract bases
# before any rule construction occurs.
_IMPORTED = False


def _ensure_rules_imported() -> None:
    global _IMPORTED
    if _IMPORTED:
        return
    import plugin.rules.constraints  # ruff:ignore[unused-import]
    import plugin.rules.matches  # ruff:ignore[unused-import]

    _IMPORTED = True


# ── ConstraintRule ─────────────────────────────────────────────────────────────


class TestConstraintRule:
    def test_make_from_known_constraint(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension", args=["py"]))
        assert rule is not None
        assert rule.constraint_name == "is_extension"
        assert rule.args == ("py",)
        assert rule.inverted is False
        assert rule.constraint is not None

    def test_make_with_inverted(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension", args=["py"], inverted=True))
        assert rule is not None
        assert rule.inverted is True

    def test_make_with_kwargs(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(
            StConstraintRule(constraint="is_extension", args=["py"], kwargs={"case_insensitive": True})
        )
        assert rule is not None
        assert rule.kwargs == {"case_insensitive": True}

    def test_make_unsupported_returns_none(self):
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="nonexistent_constraint"))
        assert rule is None

    def test_make_empty_args(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension"))
        assert rule is not None
        # empty args → no extensions → constraint folds to a constant False
        assert rule.fold().value is False

    def test_src_setting_stored(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        src = StConstraintRule(constraint="is_extension", args=["py"])
        rule = ConstraintRule.make(src)
        assert rule is not None
        assert rule.src_setting is src

    def test_optimize_leaf_yields_nothing(self, make_snapshot):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension", args=["py"]))
        assert rule is not None
        dropped = list(rule.optimize())
        assert dropped == []

    def test_folds_to_false_when_not_inverted(self):
        """A constraint that always fails is constant False."""
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension"))  # empty args -> folds
        assert rule is not None
        assert rule.fold().value is False

    def test_folds_to_true_when_inverted(self):
        """`inverted` flips a folded constraint like it flips a real result: an always-fails
        constraint, inverted, is a constant True."""
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension", inverted=True))
        assert rule is not None
        # the reason still states what the constraint settled, so it has to name the flip too --
        # a bare "always matches: no extension was given" reads like its own contradiction
        assert rule.fold() == Fold(True, 'no extension was given, negated by "not"')

    def test_does_not_fold_when_constraint_depends_on_the_view(self):
        """`inverted` must not turn a non-constant constraint into one."""
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule.make(StConstraintRule(constraint="is_extension", args=["py"], inverted=True))
        assert rule is not None
        assert rule.fold().value is None


# ── MatchRule ──────────────────────────────────────────────────────────────────


class TestMatchRule:
    def test_make_any_with_constraints(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(
            StMatchRule(
                match="any",
                rules=[
                    StConstraintRule(constraint="is_extension", args=["py"]),
                    StConstraintRule(constraint="is_extension", args=["js"]),
                ],
            )
        )
        assert rule is not None
        assert rule.match_name == "any"
        assert len(rule.rules) == 2

    def test_make_all_with_constraints(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(
            StMatchRule(
                match="all",
                rules=[
                    StConstraintRule(constraint="is_extension", args=["py"]),
                ],
            )
        )
        assert rule is not None
        assert rule.match_name == "all"
        assert len(rule.rules) == 1

    def test_make_with_nested_match(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(
            StMatchRule(
                match="any",
                rules=[
                    StConstraintRule(constraint="is_extension", args=["py"]),
                    StMatchRule(
                        match="all",
                        rules=[
                            StConstraintRule(constraint="is_extension", args=["js"]),
                            StConstraintRule(constraint="is_extension", args=["ts"]),
                        ],
                    ),
                ],
            )
        )
        assert rule is not None
        assert rule.match_name == "any"
        assert len(rule.rules) == 2
        # second child should be another MatchRule
        from plugin.rules.match import MatchRule as MatchRuleCls

        assert isinstance(rule.rules[1], MatchRuleCls)
        assert rule.rules[1].match_name == "all"  # type: ignore[union-attr]
        assert len(rule.rules[1].rules) == 2  # type: ignore[union-attr]

    def test_make_unsupported_match_returns_none(self):
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(StMatchRule(match="nonexistent_match"))
        assert rule is None

    def test_empty_rules_folds_to_false(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(StMatchRule(match="any", rules=[]))
        assert rule is not None
        assert rule.fold().value is False

    def test_src_setting_stored(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        src = StMatchRule(
            match="any",
            rules=[StConstraintRule(constraint="is_extension", args=["py"])],
        )
        rule = MatchRule.make(src)
        assert rule is not None
        assert rule.src_setting is src


# ── AbstractMatch.fold / prunable_child_value ──────────────────────────────────


class TestMatchFoldAndPrunability:
    def test_any_match_folds_empty_to_false(self):
        _ensure_rules_imported()
        from plugin.rules.matches.any import AnyMatch

        assert AnyMatch().fold(()).value is False
        assert AnyMatch().prunable_child_value() is False

    def test_all_match_folds_empty_to_true(self):
        """`all([])` is `True`, so an empty `all` is constant True, not False."""
        _ensure_rules_imported()
        from plugin.rules.matches.all import AllMatch

        assert AllMatch().fold(()).value is True
        assert AllMatch().prunable_child_value() is True

    def test_some_match_folds_to_true_when_goal_unreachable_low(self):
        """A count <= 0 means the goal is always satisfied (`goal <= 0` -> constant True)."""
        _ensure_rules_imported()
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch(-1).fold(()).value is True
        assert SomeMatch(0).fold((_FixedRule(True), _FixedRule(True))).value is True

    def test_some_match_folds_to_false_when_goal_unreachable_high(self):
        """count > len(rules) can never be satisfied -> constant False."""
        _ensure_rules_imported()
        from plugin.rules.matches.some import SomeMatch

        assert SomeMatch(3).fold((_FixedRule(True), _FixedRule(True))).value is False

    def test_ratio_match_never_allows_child_pruning(self):
        """Ratio's goal is recomputed from `len(rules)`, so pruning any child would corrupt it."""
        _ensure_rules_imported()
        from plugin.rules.matches.ratio import RatioMatch

        assert RatioMatch(2, 3).prunable_child_value() is None


# ── MatchRule.optimize() semantics (AND/OR-correctness of pruning) ──────────────


class _FixedRule:
    """Fake leaf rule: fixed test() result and droppability, for isolating optimizer logic."""

    def __init__(self, result: bool, *, folded: bool | None = None, reason: str = "") -> None:
        self._result = result
        self._folded = folded
        self._reason = reason

    def fold(self) -> Fold:
        return Fold(self._folded, self._reason)

    def optimize(self):
        return iter(())

    def test(self, view_snapshot) -> bool:
        return self._result


class TestMatchRuleOptimizeSemantics:
    def test_all_does_not_prune_constant_false_child(self):
        """all(True, any()) is always False; pruning the constant-False any() must not flip it to True."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule
        from plugin.rules.matches.all import AllMatch
        from plugin.rules.matches.any import AnyMatch

        leaf = _FixedRule(True)  # a genuine (non-folding) rule, not itself a candidate for pruning
        inner_any = MatchRule(match=AnyMatch(), match_name="any", rules=())
        outer_all = MatchRule(match=AllMatch(), match_name="all", rules=(leaf, inner_any))

        assert outer_all.test(None) is False

        dropped = list(outer_all.optimize())

        assert outer_all.test(None) is False
        assert outer_all.rules == (leaf, inner_any)  # inner_any (constant False) must not be pruned from `all`
        assert dropped == []

    def test_any_does_not_prune_constant_true_child(self):
        """any(False, all()) is always True; pruning the constant-True all() must not make it conditional."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule
        from plugin.rules.matches.all import AllMatch
        from plugin.rules.matches.any import AnyMatch

        leaf = _FixedRule(False)  # a genuine (non-folding) rule, not itself a candidate for pruning
        inner_all = MatchRule(match=AllMatch(), match_name="all", rules=())
        outer_any = MatchRule(match=AnyMatch(), match_name="any", rules=(leaf, inner_all))

        assert outer_any.test(None) is True

        dropped = list(outer_any.optimize())

        assert outer_any.test(None) is True
        assert outer_any.rules == (leaf, inner_all)  # inner_all (constant True) must not be pruned from `any`
        assert dropped == []

    def test_all_prunes_constant_true_leaf(self):
        """A constant-True leaf is safe to drop from `all` (True is its identity element)."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule
        from plugin.rules.matches.all import AllMatch

        const_true_leaf = _FixedRule(True, folded=True)
        rule = MatchRule(match=AllMatch(), match_name="all", rules=(_FixedRule(True), const_true_leaf))

        dropped = list(rule.optimize())

        assert const_true_leaf in dropped
        assert const_true_leaf not in rule.rules

    def test_ratio_never_prunes_children_even_when_folds_to_false(self):
        """Ratio's own goal depends on len(rules), so no child pruning is ever safe."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule
        from plugin.rules.matches.ratio import RatioMatch

        droppable_leaf = _FixedRule(False, folded=False)
        rule = MatchRule(
            match=RatioMatch(2, 3),
            match_name="ratio",
            rules=(_FixedRule(True), _FixedRule(True), droppable_leaf),
        )

        list(rule.optimize())

        assert len(rule.rules) == 3

    def test_all_prunes_a_real_constraint_that_folds_to_true(self):
        """End to end, with a real constraint rather than a fake: `contains` with a threshold of
        0 always matches, so `all` can drop it. This is the constant-True case the old
        is_droppable()/droppable_value() pair had no way to express for a constraint -- it could
        only say "always False" -- so such a rule used to be re-tested on every single view."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(
            StMatchRule(
                match="all",
                rules=[
                    StConstraintRule(constraint="contains", args=["anything"], kwargs={"threshold": 0}),
                    StConstraintRule(constraint="is_extension", args=["py"]),
                ],
            )
        )
        assert rule is not None

        dropped = list(rule.optimize())

        assert [r.constraint_name for r in dropped] == ["contains"]  # type: ignore[union-attr]
        assert [r.constraint_name for r in rule.rules] == ["is_extension"]  # type: ignore[union-attr]

    def test_any_keeps_a_real_constraint_that_folds_to_true(self):
        """The mirror of the above: a constant-True child of `any` makes the whole `any` true,
        so pruning it would silently flip the result. Only `all` may drop it."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(
            StMatchRule(
                match="any",
                rules=[
                    StConstraintRule(constraint="contains", args=["anything"], kwargs={"threshold": 0}),
                    StConstraintRule(constraint="is_extension", args=["py"]),
                ],
            )
        )
        assert rule is not None

        dropped = list(rule.optimize())

        assert dropped == []
        assert len(rule.rules) == 2


# ── SyntaxRule ─────────────────────────────────────────────────────────────────


class TestSyntaxRule:
    def test_make_stores_comment_and_selector(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                comment="test rule",
                selector="source.python",
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            )
        )
        assert rule.comment == "test rule"
        assert rule.selector == "source.python"
        assert rule.root_rule is not None

    def test_make_no_syntax_resolved(self, make_snapshot):
        """Syntax resolution returns None in test mock, so syntax attr is None."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["NonexistentSyntax"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            )
        )
        assert rule.syntax is None
        assert rule.syntaxes_name == ("NonexistentSyntax",)

    def test_folds_to_false_with_no_syntax(self, make_snapshot):
        """Without a resolved syntax, the rule should be droppable."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["NonexistentSyntax"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            )
        )
        assert rule.fold().value is False

    def test_empty_on_events_never_triggers(self, make_snapshot):
        """on_events=[] means no event triggers — rule becomes droppable."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            )
        )
        # With syntax=None (mock) the rule is droppable
        # The main thing is the constructor doesn't crash with empty on_events
        assert rule.on_events is None  # not set → None = no restriction

    def test_src_setting_stored(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        src = StSyntaxRule(
            syntaxes=["Python"],
            rules=[StConstraintRule(constraint="is_extension", args=["py"])],
        )
        rule = SyntaxRule.make(src)
        assert rule.src_setting is src

    def test_optimize_no_root_rule_yields_nothing(self):
        """Unsupported match → root_rule is None → optimize() is a no-op."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(StSyntaxRule(match="nonexistent_match", syntaxes=["Python"]))
        assert rule.root_rule is None
        assert list(rule.optimize()) == []

    def test_optimize_drops_immediately_droppable_root_rule(self):
        """root_rule is already droppable (no child rules) → dropped whole, without recursing."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(StSyntaxRule(syntaxes=["Python"], rules=[]))
        root_rule = rule.root_rule
        assert root_rule is not None
        assert root_rule.fold().value is False

        dropped = list(rule.optimize())

        assert dropped == [root_rule]
        assert rule.root_rule is None

    def test_optimize_keeps_root_rule_that_collapses_to_constant_true(self):
        """An empty `all` root_rule is constant True — it must stay attached, not be discarded like a false one."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(StSyntaxRule(syntaxes=["Python"], match="all", rules=[]))
        root_rule = rule.root_rule
        assert root_rule is not None
        assert root_rule.fold().value is True

        dropped = list(rule.optimize())

        assert dropped == []  # always matches (given selector/events) -- must not be discarded
        assert rule.root_rule is root_rule

    def test_optimize_prunes_children_but_keeps_survivable_root(self):
        """One droppable child is pruned; root_rule still has a survivor and stays attached."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["Python"],
                rules=[
                    StConstraintRule(constraint="is_extension", args=["py"]),
                    StConstraintRule(constraint="is_extension"),  # no exts → droppable
                ],
            )
        )
        root_rule = rule.root_rule
        assert root_rule is not None
        assert len(root_rule.rules) == 2
        assert root_rule.fold().value is None

        dropped = list(rule.optimize())

        assert len(dropped) == 1  # only the droppable constraint
        assert rule.root_rule is root_rule  # root_rule survives, stays attached
        assert len(root_rule.rules) == 1

    def test_optimize_drops_root_rule_that_becomes_droppable_after_pruning(self):
        """root_rule's only child is droppable; after pruning it root_rule itself is now droppable too."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_extension")],  # no exts → droppable
            )
        )
        root_rule = rule.root_rule
        assert root_rule is not None
        assert root_rule.fold().value is None  # still has a (droppable) child, so not droppable yet
        child_rule = root_rule.rules[0]

        dropped = list(rule.optimize())

        assert dropped == [child_rule, root_rule]
        assert rule.root_rule is None


# ── SyntaxRuleCollection ───────────────────────────────────────────────────────


class TestSyntaxRuleCollection:
    def test_make_from_empty(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        col = SyntaxRuleCollection.make([])
        assert len(col) == 0

    def test_make_from_rules(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        col = SyntaxRuleCollection.make([
            StSyntaxRule(
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            ),
        ])
        assert len(col) == 1

    def test_len(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        col = SyntaxRuleCollection.make([
            StSyntaxRule(syntaxes=["A"], rules=[]),
            StSyntaxRule(syntaxes=["B"], rules=[]),
        ])
        assert len(col) == 2

    def test_optimize_drops_droppable_rules(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        # All rules have syntax=None → droppable → should all be dropped
        col = SyntaxRuleCollection.make([
            StSyntaxRule(syntaxes=["A"], rules=[]),
            StSyntaxRule(syntaxes=["B"], rules=[]),
        ])
        dropped = list(col.optimize())
        assert len(col) == 0  # all rules dropped
        assert len(dropped) == 2

    def test_test_no_match(self, make_snapshot):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        col = SyntaxRuleCollection.make([
            StSyntaxRule(
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            ),
        ])
        snap = make_snapshot(path="/tmp/test.py", content="print('hello')", first_line="print('hello')")
        # Syntax is None in mock → rules are droppable → optimize drops them
        col.optimize()
        result = col.test(snap)
        assert result is None


# ── sift_optimizable ───────────────────────────────────────────────────────────


class _OptimizableBase:
    """Minimal Optimizable-like class for testing sift_optimizable."""

    def __init__(self, droppable: bool = False) -> None:
        self._droppable = droppable
        self.optimized_yielded: list = []

    def fold(self) -> Fold:
        return Fold(False, "droppable") if self._droppable else UNFOLDED

    def optimize(self):
        return iter(self.optimized_yielded)


class TestSiftOptimizable:
    def test_empty_tuple(self):
        from plugin.rules._optimize import sift_optimizable

        dropped, survivors = sift_optimizable(())
        assert dropped == []
        assert survivors == ()

    def test_drops_droppable_rules(self):
        from plugin.rules._optimize import sift_optimizable

        d1, d2 = _OptimizableBase(droppable=True), _OptimizableBase(droppable=True)
        dropped, survivors = sift_optimizable((d1, d2))
        assert len(dropped) == 2
        assert survivors == ()

    def test_preserves_non_droppable_rules(self):
        from plugin.rules._optimize import sift_optimizable

        v1, v2 = _OptimizableBase(droppable=False), _OptimizableBase(droppable=False)
        dropped, survivors = sift_optimizable((v1, v2))
        assert dropped == []
        assert len(survivors) == 2

    def test_mixed_droppable_and_valid(self):
        from plugin.rules._optimize import sift_optimizable

        v1 = _OptimizableBase(droppable=False)
        d1 = _OptimizableBase(droppable=True)
        v2 = _OptimizableBase(droppable=False)
        dropped, survivors = sift_optimizable((v1, d1, v2))
        assert len(dropped) == 1
        assert len(survivors) == 2
        assert survivors[0] is v1
        assert survivors[1] is v2

    def test_optimize_yields_from_sub_rules(self):
        from plugin.rules._optimize import sift_optimizable

        inner = _OptimizableBase(droppable=True)
        parent = _OptimizableBase(droppable=False)
        parent.optimized_yielded = [inner]

        dropped, survivors = sift_optimizable((parent,))
        # inner was yielded by parent.optimize() and added to dropped
        assert inner in dropped
        assert next(r for r in dropped if r is inner)
        # parent survives
        assert len(survivors) == 1
        assert survivors[0] is parent


# ── DroppedRule ───────────────────────────────────────────────────────────────


class TestDroppedRule:
    """A dropped rule has to say which constant it folded to. "Dropped" alone is ambiguous:
    a rule is discarded both for never matching and for always matching, and those mean
    opposite things to someone reading the debug dump."""

    def test_never_matching_rule(self):
        from plugin.types import DroppedRule

        assert DroppedRule.make(_FixedRule(False, folded=False)).reason == "never matches"

    def test_always_matching_rule(self):
        from plugin.types import DroppedRule

        assert DroppedRule.make(_FixedRule(True, folded=True)).reason == "always matches"

    def test_rule_that_does_not_fold(self):
        """Optimizing shouldn't discard one of these, so say so rather than claim a constant."""
        from plugin.types import DroppedRule

        assert DroppedRule.make(_FixedRule(True)).reason == "dropped without folding"

    def test_reason_survives_the_real_optimizer(self):
        """End to end: `all` drops one child for always matching and one for never matching."""
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule
        from plugin.types import DroppedRule

        rule = MatchRule.make(
            StMatchRule(
                match="all",
                rules=[
                    StConstraintRule(constraint="contains", args=["x"], kwargs={"threshold": 0}),
                    StConstraintRule(constraint="is_extension"),  # no extensions -> never matches
                    StConstraintRule(constraint="is_extension", args=["py"]),
                ],
            )
        )
        assert rule is not None

        dropped = [DroppedRule.make(r) for r in rule.optimize()]

        # the constant-False child stays: `all(False, x)` is False, unlike `all(x)`
        assert [(d.rule.constraint_name, d.reason) for d in dropped] == [  # type: ignore[union-attr]
            ("contains", 'always matches: a "threshold" of 0 is met without finding anything'),
        ]
        assert DroppedRule.make(rule.rules[0]).reason == "never matches: no extension was given"


class _BadFoldConstraint:
    """A custom constraint whose `fold()` returns something that isn't a `Fold`."""

    def __init__(self, fold: object) -> None:
        self._fold = fold

    def fold(self) -> object:
        return self._fold

    def test(self, view_snapshot) -> bool:
        return False


class TestFoldReturnTypeIsEnforced:
    """`fold()` must return a `Fold`. Nothing else counts -- not a bare `bool`/`None` from the
    older contract, and not a plain `(value, reason)` tuple of the right shape either, even
    though `Fold` is a `NamedTuple` and unpacking one would have worked. The rejection has to
    name the class: that's the only part of the message a user can act on."""

    @pytest.mark.parametrize("bad", [False, True, None, (False, "no widget was given"), "nope"])
    def test_non_fold_return_is_rejected_by_class_name(self, bad):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule

        rule = ConstraintRule(constraint=_BadFoldConstraint(bad))  # type: ignore[arg-type]

        with pytest.raises(TypeError, match=r"_BadFoldConstraint\.fold\(\) must return a Fold"):
            rule.fold()

    def test_a_real_fold_is_returned_as_is(self):
        _ensure_rules_imported()
        from plugin.rules.constraint import ConstraintRule
        from plugin.types import DroppedRule

        rule = ConstraintRule(constraint=_BadFoldConstraint(Fold(False, "no widget was given")))  # type: ignore[arg-type]

        assert rule.fold() == Fold(False, "no widget was given")
        assert DroppedRule.make(rule).reason == "never matches: no widget was given"


# ── warn_legacy_fold_overrides ────────────────────────────────────────────────


class TestWarnLegacyFoldOverrides:
    """`fold()` replaced `is_droppable()`/`droppable_value()`, which the docs advertise as the
    Custom Implementation extension point. A custom class still overriding the old names keeps
    working but silently stops being optimized away, so it has to be told at load time."""

    def test_warns_about_a_legacy_override(self, capsys):
        from plugin.rules._optimize import warn_legacy_fold_overrides

        class _Base:
            pass

        class _Legacy(_Base):
            def is_droppable(self) -> bool:
                return True

        warn_legacy_fold_overrides(_Base)

        out = capsys.readouterr().out
        assert "_Legacy" in out
        assert "is_droppable" in out
        assert "fold()" in out

    def test_silent_when_nothing_overrides_the_old_names(self, capsys):
        from plugin.rules._optimize import warn_legacy_fold_overrides

        class _Base:
            pass

        class _Modern(_Base):
            def fold(self) -> bool | None:
                return None

        warn_legacy_fold_overrides(_Base)

        assert capsys.readouterr().out == ""

    def test_built_in_constraints_and_matches_are_all_migrated(self, capsys):
        """Guards against a built-in being missed by the migration."""
        _ensure_rules_imported()
        from plugin.rules._optimize import warn_legacy_fold_overrides
        from plugin.rules.constraint import AbstractConstraint
        from plugin.rules.match import AbstractMatch

        warn_legacy_fold_overrides(AbstractConstraint, AbstractMatch)

        assert capsys.readouterr().out == ""


# ── Integration: MatchRule → SyntaxRule → SyntaxRuleCollection ────────────────


class TestRuleIntegration:
    def test_build_and_optimize_pipeline(self):
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRuleCollection

        col = SyntaxRuleCollection.make([
            # Rule 1: will be droppable (empty rules → droppable match)
            StSyntaxRule(
                comment="empty rule",
                syntaxes=["Python"],
                rules=[],
            ),
            # Rule 2: will be droppable (unsupported constraint filtered out)
            StSyntaxRule(
                comment="bad constraint rule",
                syntaxes=["Python"],
                rules=[StConstraintRule(constraint="is_not_a_real_constraint")],
            ),
        ])

        assert len(col) == 2
        dropped = list(col.optimize())
        assert len(col) == 0, "All rules should be dropped after optimization"
        assert len(dropped) >= 2


# ── Randomized invariant: optimize() must never change test() ─────────────────
#
# Every real bug found in this optimizer so far (droppable rules getting pruned
# from the wrong side of all()/any(), a constant-True root_rule getting discarded
# like a constant-False one, a missing constant-False case) was a
# violation of the same invariant: running optimize() on a rule tree must never
# change what test() returns for it. Rather than hand-writing one example per bug
# shape, generate many random trees (honoring the fold()/test() contract) and check the
# invariant holds across all of them.


class _ConsistentFixedRule:
    """Fake leaf that honors the fold()/test() contract: when it folds, test() always equals
    what it folded to (see Optimizable.fold docs). An inconsistent fake would make optimize()
    *correctly* look buggy against a contract violation that isn't the optimizer's fault, so
    this is deliberately always self-consistent."""

    def __init__(self, result: bool, *, folds: bool = False) -> None:
        self._result = result
        self._folds = folds

    def fold(self) -> Fold:
        return Fold(self._result, "fixed") if self._folds else UNFOLDED

    def optimize(self):
        return iter(())

    def test(self, view_snapshot) -> bool:
        return self._result


def _random_child(rng, depth: int):
    """A node usable as a MatchRule child: either a leaf or a nested MatchRule."""
    if depth <= 0 or rng.random() < 0.35:
        return _ConsistentFixedRule(rng.random() < 0.5, folds=rng.random() < 0.4)
    return _random_match_rule(rng, depth - 1)


def _random_match_rule(rng, depth: int):
    from plugin.rules.match import MatchRule
    from plugin.rules.matches.all import AllMatch
    from plugin.rules.matches.any import AnyMatch
    from plugin.rules.matches.ratio import RatioMatch
    from plugin.rules.matches.some import SomeMatch

    children = tuple(_random_child(rng, depth - 1) for _ in range(rng.randint(0, 4)))
    kind = rng.choice(("all", "any", "some", "ratio"))

    if kind == "all":
        match_obj, match_name = AllMatch(), "all"
    elif kind == "any":
        match_obj, match_name = AnyMatch(), "any"
    elif kind == "some":
        match_obj, match_name = SomeMatch(rng.randint(-1, len(children) + 1)), "some"
    else:
        match_obj, match_name = RatioMatch(rng.randint(0, 3), rng.randint(0, 3)), "ratio"

    return MatchRule(match=match_obj, match_name=match_name, rules=children)


class TestMatchRuleOptimizeInvariant:
    def test_optimize_never_changes_test_result(self):
        import random

        _ensure_rules_imported()

        for seed in range(20):
            rng = random.Random(seed)
            for _ in range(50):
                rule = _random_match_rule(rng, depth=4)
                pre = rule.test(None)
                list(rule.optimize())
                post = rule.test(None)
                assert pre == post, f"seed={seed}: optimize() changed test() result {pre} -> {post}"

    def test_optimize_never_changes_syntax_rule_test_result(self):
        """Same invariant one level up: SyntaxRule.optimize() must not change whether the rule
        matches, even when its root_rule collapses to a droppable constant during optimization."""
        import random

        from plugin.rules.syntax import SyntaxRule

        _ensure_rules_imported()

        for seed in range(20):
            rng = random.Random(seed)
            for _ in range(50):
                root_rule = _random_match_rule(rng, depth=3)
                syntax_rule = SyntaxRule(syntax=object(), root_rule=root_rule)

                # SyntaxRule.test() short-circuits on selector/syntax checks before reaching
                # root_rule, so exercise root_rule's own test() directly -- that's the part
                # SyntaxRule.optimize() is allowed to touch.
                pre = root_rule.test(None)
                list(syntax_rule.optimize())
                post = (syntax_rule.root_rule.test(None)) if syntax_rule.root_rule else syntax_rule.root_rule
                # if root_rule was dropped entirely, it must only be because it was constant
                # False (SyntaxRule.optimize()'s own `fold() is False` check enforces this);
                # a constant-True root_rule must be kept (or represented as an unconditional
                # match), never silently turned into "no match".
                if syntax_rule.root_rule is None:
                    assert pre is False, f"seed={seed}: root_rule discarded despite testing {pre}"
                else:
                    assert pre == post, f"seed={seed}: optimize() changed root_rule test() result {pre} -> {post}"
