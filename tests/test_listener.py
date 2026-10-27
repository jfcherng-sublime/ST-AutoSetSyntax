"""Tests for AutoSetSyntaxEventListener's on_new/on_new_window window-setup ordering.

Regression coverage: Sublime Text fires `on_new(view)` *before* `on_new_window(window)` for a
brand new window's first tab. `on_new_window` is what compiles a window's rule collection
(`G.syntax_rule_collections`), which `run_auto_set_syntax_on_view()` requires via
`G.is_plugin_ready()`. Without ensuring setup runs first, the NEW event -- and therefore
`new_file_syntax` -- would silently never apply to a new window's first tab.
"""

from unittest.mock import MagicMock

import sublime

import plugin.listener as listener_mod
from plugin.settings import SyntaxRulesLoad
from plugin.shared import G


def _make_window(window_id: int) -> MagicMock:
    window = MagicMock(spec=sublime.Window)
    window.id.return_value = window_id
    return window


class TestEnsureWindowSetUp:
    def test_calls_set_up_window_when_not_yet_tracked(self, monkeypatch):
        window = _make_window(101)
        assert window not in G.syntax_rule_collections

        calls = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

        listener_mod._ensure_window_set_up(window)

        assert calls == [window]

    def test_skips_set_up_window_when_already_tracked(self, monkeypatch):
        from plugin.rules import SyntaxRuleCollection

        window = _make_window(102)
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])
        try:
            calls = []
            monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

            listener_mod._ensure_window_set_up(window)

            assert calls == []
        finally:
            G.syntax_rule_collections.pop(window, None)


class TestOnNewEnsuresWindowSetUpBeforeEvaluating:
    def test_on_new_sets_up_window_before_running_auto_set_syntax(self, monkeypatch):
        window = _make_window(103)
        view = MagicMock()
        view.window.return_value = window
        assert window not in G.syntax_rule_collections

        call_order = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: call_order.append("set_up_window"))
        monkeypatch.setattr(
            listener_mod,
            "run_auto_set_syntax_on_view",
            lambda v, event, **kwargs: call_order.append("run_auto_set_syntax_on_view"),
        )

        listener_mod.AutoSetSyntaxEventListener().on_new(view)

        assert call_order == ["set_up_window", "run_auto_set_syntax_on_view"]

    def test_on_new_does_not_redundantly_set_up_an_already_tracked_window(self, monkeypatch):
        from plugin.rules import SyntaxRuleCollection

        window = _make_window(104)
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])
        try:
            view = MagicMock()
            view.window.return_value = window

            calls = []
            monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))
            monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kwargs: True)

            listener_mod.AutoSetSyntaxEventListener().on_new(view)

            assert calls == []
        finally:
            G.syntax_rule_collections.pop(window, None)


class TestOnNewWindowStillSetsUpWhenOnNewDidNotRunFirst:
    def test_on_new_window_sets_up_window_when_not_yet_tracked(self, monkeypatch):
        window = _make_window(105)
        assert window not in G.syntax_rule_collections

        calls = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

        listener_mod.AutoSetSyntaxEventListener().on_new_window(window)

        assert calls == [window]


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
            listener_mod.compile_rules(window)  # must not raise

            assert len(G.syntax_rule_collections[window]) == 1
            [dropped] = G.dropped_rules_collection[window]
            assert dropped.reason.startswith("invalid setting at user_syntax_rules[0]: ")
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)

    def test_invalid_rules_stay_reported_when_optimizing_fails(self, monkeypatch):
        """The unoptimized fallback must not forget the rules that never got that far."""
        from plugin.rules import SyntaxRuleCollection
        from plugin.types import DroppedRule

        window = _make_window(108)
        invalid = DroppedRule.invalid("user_syntax_rules[0]", {"constrait": "x"}, "boom")
        monkeypatch.setattr(
            listener_mod, "pref_syntax_rules", lambda *, window=None: SyntaxRulesLoad([], [invalid], ())
        )

        def _broken_optimize(self):
            raise RuntimeError("optimizer broke")
            yield

        monkeypatch.setattr(SyntaxRuleCollection, "optimize", _broken_optimize)

        try:
            listener_mod.compile_rules(window)

            assert G.dropped_rules_collection[window] == [invalid]
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)


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
            listener_mod,
            "pref_syntax_rules",
            lambda *, window=None: SyntaxRulesLoad(
                [
                    (
                        StSyntaxRule(
                            syntaxes=["Python"],
                            selector="",
                            rules=[StConstraintRule(constraint="broken_fold")],
                        ),
                        "user_syntax_rules",
                    )
                ],
                [],
                (),
            ),
        )
        monkeypatch.setattr("plugin.rules.syntax.find_syntax", lambda *args, **kwargs: syntax)

        logged: list[str] = []
        monkeypatch.setattr(
            listener_mod.Logger,
            "log",
            staticmethod(lambda msg, **kwargs: logged.append(msg() if callable(msg) else msg)),
        )

        try:
            listener_mod.compile_rules(window)  # must not raise

            # the rule survived unoptimized, still holding the root that `SyntaxRule.test()`
            # asserts on -- a half-pruned tree would have detached it
            collection = G.syntax_rule_collections[window]
            assert len(collection) == 1
            assert collection.rules[0].root_rule is not None
            assert G.dropped_rules_collection[window] == []

            # naming the class is the whole point: "cannot unpack non-iterable bool object"
            # would leave the user guessing which of their custom implementations broke
            failure = next(msg for msg in logged if msg.startswith("❌"))
            assert "BrokenFoldConstraint.fold() must return a Fold" in failure
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)


class TestCompileRulesKeepsTheRuleOrigin:
    """A rule from another package's file has to stay attributable *after* it's compiled: a rule
    discarded while optimizing has nothing left in its reason naming the file, and "which package
    gave me this rule?" is the question a user with a misbehaving package actually asks."""

    def test_a_dropped_package_rule_names_its_file(self, monkeypatch):
        from plugin.types import StSyntaxRule

        window = _make_window(108)
        origin = "Packages/Foo/AutoSetSyntax.rules.v1.sublime-settings"
        # no matching syntax available -> the rule folds to "never matches" and gets dropped
        monkeypatch.setattr("plugin.rules.syntax.find_syntax", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            listener_mod,
            "pref_syntax_rules",
            lambda *, window=None: SyntaxRulesLoad([(StSyntaxRule(syntaxes=["NoSuchSyntax"]), origin)], [], ()),
        )
        monkeypatch.setattr(listener_mod.Logger, "log", staticmethod(lambda msg, **kwargs: None))

        try:
            listener_mod.compile_rules(window)

            [dropped] = G.dropped_rules_collection[window]
            assert dropped.origin == origin
            assert dropped.reason.startswith("never matches")
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)

    def test_a_rule_from_settings_keeps_its_setting_as_origin(self, monkeypatch):
        """Optimizing discards a rule without leaving any location in its reason, so the origin is
        the only thing that still says whether a dropped rule was the user's own or a package's."""
        from plugin.types import StSyntaxRule

        window = _make_window(109)
        monkeypatch.setattr("plugin.rules.syntax.find_syntax", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            listener_mod,
            "pref_syntax_rules",
            lambda *, window=None: SyntaxRulesLoad(
                [(StSyntaxRule(syntaxes=["NoSuchSyntax"]), "user_syntax_rules")], [], ()
            ),
        )
        monkeypatch.setattr(listener_mod.Logger, "log", staticmethod(lambda msg, **kwargs: None))

        try:
            listener_mod.compile_rules(window)

            [dropped] = G.dropped_rules_collection[window]
            assert dropped.origin == "user_syntax_rules"
            assert "user_syntax_rules" not in dropped.reason
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)


class TestCompileRulesReportsWhichPackagesContribute:
    """The log panel is how a user answers "which package is setting my syntax?". Naming the
    packages is the only thing that answers it -- once compiled, the rules look like any other."""

    @staticmethod
    def _compile(monkeypatch, load) -> list[str]:
        window = _make_window(110)
        monkeypatch.setattr(listener_mod, "pref_syntax_rules", lambda *, window=None: load)
        logged: list[str] = []
        monkeypatch.setattr(
            listener_mod.Logger,
            "log",
            staticmethod(lambda msg, **kwargs: logged.append(msg() if callable(msg) else msg)),
        )
        try:
            listener_mod.compile_rules(window)
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)
        return logged

    def test_names_the_packages_that_ship_rules(self, monkeypatch):
        logged = self._compile(
            monkeypatch,
            SyntaxRulesLoad(
                [], [], ("Packages/Foo/AutoSetSyntax.rules.v1.sublime-settings",), package_rules_enabled=True
            ),
        )

        summary = next(msg for msg in logged if msg.startswith("📦"))
        assert "Foo" in summary

    def test_reports_a_package_only_once_even_with_several_files(self, monkeypatch):
        logged = self._compile(
            monkeypatch,
            SyntaxRulesLoad(
                [],
                [],
                (
                    "Packages/Foo/AutoSetSyntax.rules.v1.sublime-settings",
                    "Packages/Foo/AutoSetSyntax.rules.v1.extra.sublime-settings",
                ),
                package_rules_enabled=True,
            ),
        )

        summary = next(msg for msg in logged if msg.startswith("📦"))
        assert summary.count('"Foo"') == 1

    def test_says_so_when_no_package_ships_any(self, monkeypatch):
        """ "Nothing found" and "the feature is off" are different answers to the same question."""
        logged = self._compile(monkeypatch, SyntaxRulesLoad([], [], (), package_rules_enabled=True))

        assert any("none" in msg for msg in logged if msg.startswith("📦"))

    def test_says_so_when_the_feature_is_switched_off(self, monkeypatch):
        window = _make_window(111)
        monkeypatch.setattr(
            listener_mod,
            "pref_syntax_rules",
            lambda *, window=None: SyntaxRulesLoad([], [], (), package_rules_enabled=False),
        )
        logged: list[str] = []
        monkeypatch.setattr(
            listener_mod.Logger,
            "log",
            staticmethod(lambda msg, **kwargs: logged.append(msg() if callable(msg) else msg)),
        )
        try:
            listener_mod.compile_rules(window)
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)

        assert any("disabled" in msg for msg in logged if msg.startswith("📦"))
