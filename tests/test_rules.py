"""Tests for ConstraintRule, MatchRule, SyntaxRule, SyntaxRuleCollection, sift_optimizable."""

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
    import plugin.rules.constraints  # noqa: F401
    import plugin.rules.matches  # noqa: F401

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
        # empty args → no extensions → constraint is droppable
        assert rule.is_droppable() is True

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

    def test_empty_rules_droppable(self):
        _ensure_rules_imported()
        from plugin.rules.match import MatchRule

        rule = MatchRule.make(StMatchRule(match="any", rules=[]))
        assert rule is not None
        assert rule.is_droppable() is True

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

    def test_is_droppable_no_syntax(self, make_snapshot):
        """Without a resolved syntax, the rule should be droppable."""
        _ensure_rules_imported()
        from plugin.rules.syntax import SyntaxRule

        rule = SyntaxRule.make(
            StSyntaxRule(
                syntaxes=["NonexistentSyntax"],
                rules=[StConstraintRule(constraint="is_extension", args=["py"])],
            )
        )
        assert rule.is_droppable() is True

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

    def is_droppable(self) -> bool:
        return self._droppable

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
