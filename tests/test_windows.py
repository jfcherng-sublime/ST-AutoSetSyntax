"""Tests for compiling a window's syntax rules (plugin/windows.py)."""

from unittest.mock import MagicMock

import sublime

import plugin.windows as windows_mod
from plugin.shared import G


def _make_window(window_id: int) -> MagicMock:
    window = MagicMock(spec=sublime.Window)
    window.id.return_value = window_id
    return window


class TestCompileRulesHandlesInvalidSyntaxRules:
    """StConstraintRule/StMatchRule reject unrecognized keys (a typo'd "constraint" key would
    otherwise silently validate as a no-op StMatchRule). One such rule used to fail validation of
    the whole merged list, so compile_rules() fell back to *no* rules at all -- the bundled ones
    included. Only the malformed rule may go, and it must show up in Debug Information."""

    def test_invalid_rule_is_dropped_alone_and_reported(self, monkeypatch):
        import plugin.rules.constraints  # ruff:ignore[unused-import]

        window = _make_window(106)
        syntax = sublime.Syntax("Packages/Python/Python.sublime-syntax", "Python", False, "source.python")
        monkeypatch.setattr("plugin.rules.syntax.find_syntax", lambda *args, **kwargs: syntax)
        monkeypatch.setattr(
            "plugin.settings.get_merged_plugin_settings",
            lambda **kwargs: {
                "user_syntax_rules": [
                    # a typo'd "constraint" key, same shape as a real user config mistake
                    {"rules": [{"constrait": "is_extension", "args": ["py"]}]},
                    {"selector": "", "rules": [{"constraint": "is_extension", "args": ["py"]}]},
                ],
            },
        )

        try:
            windows_mod.compile_rules(window)  # must not raise

            assert len(G.compiled_rules[window].collection) == 1
            [dropped] = G.compiled_rules[window].dropped
            assert dropped.reason.startswith("invalid setting at user_syntax_rules[0]: ")
        finally:
            G.compiled_rules.pop(window, None)

    def test_invalid_rules_stay_reported_when_optimizing_fails(self, monkeypatch):
        """The unoptimized fallback must not forget the rules that never got that far."""
        from plugin.rules import SyntaxRuleCollection
        from plugin.types import DroppedRule

        window = _make_window(108)
        invalid = DroppedRule.invalid("user_syntax_rules[0]", {"constrait": "x"}, "boom")
        monkeypatch.setattr(windows_mod, "pref_syntax_rules", lambda *, window=None: ([], [invalid]))

        def _broken_optimize(self):
            raise RuntimeError("optimizer broke")
            yield

        monkeypatch.setattr(SyntaxRuleCollection, "optimize", _broken_optimize)

        try:
            windows_mod.compile_rules(window)

            assert G.compiled_rules[window].dropped == [invalid]
        finally:
            G.compiled_rules.pop(window, None)


class TestCompileRulesSurvivesABrokenFold:
    """`fold()` must return a `Fold`, but a Custom Implementation is user code we only find out
    about at compile time. Optimizing prunes the tree as it walks it, so letting the failure
    escape would both kill `set_up_window()` for the whole window and leave a half-pruned
    collection behind. Fall back to the unoptimized rules instead."""

    def test_bad_fold_keeps_the_rules_usable(self, monkeypatch):
        from plugin.rules import AbstractConstraint
        from plugin.types import StConstraintRule
        from plugin.types import StSyntaxRule

        class BrokenFoldConstraint(AbstractConstraint):
            """A custom constraint still written against the old bare-`bool | None` contract."""

            def fold(self):  # type: ignore[override]
                return False

            def test(self, view_snapshot) -> bool:
                return True

        window = _make_window(107)
        syntax = sublime.Syntax("Packages/Python/Python.sublime-syntax", "Python", False, "source.python")
        monkeypatch.setattr(
            windows_mod,
            "pref_syntax_rules",
            lambda *, window=None: (
                [
                    StSyntaxRule(
                        syntaxes=["Python"],
                        selector="",
                        rules=[StConstraintRule(constraint="broken_fold")],
                    )
                ],
                [],
            ),
        )
        monkeypatch.setattr("plugin.rules.syntax.find_syntax", lambda *args, **kwargs: syntax)

        logged: list[str] = []
        monkeypatch.setattr(
            windows_mod.Logger,
            "log",
            staticmethod(lambda msg, **kwargs: logged.append(msg() if callable(msg) else msg)),
        )

        try:
            windows_mod.compile_rules(window)  # must not raise

            # the rule survived unoptimized, still holding the root that `SyntaxRule.test()`
            # asserts on -- a half-pruned tree would have detached it
            collection = G.compiled_rules[window].collection
            assert len(collection) == 1
            assert collection.rules[0].root_rule is not None
            assert G.compiled_rules[window].dropped == []

            # naming the class is the whole point: "cannot unpack non-iterable bool object"
            # would leave the user guessing which of their custom implementations broke
            failure = next(msg for msg in logged if msg.startswith("❌"))
            assert "BrokenFoldConstraint.fold() must return a Fold" in failure
        finally:
            G.compiled_rules.pop(window, None)
