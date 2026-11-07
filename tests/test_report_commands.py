"""Tests for the commands that report on the compiled rules: Debug Information and Syntax Rules Summary."""

from unittest.mock import MagicMock

import pytest
import sublime

import plugin.commands.auto_set_syntax_debug_information as debug_mod
import plugin.commands.auto_set_syntax_syntax_rules_summary as summary_mod
from plugin.shared import CompiledRules
from plugin.shared import G
from plugin.types import DroppedRule
from plugin.types import StSyntaxRule


@pytest.fixture
def window():
    window = MagicMock(spec=sublime.Window)
    window.id.return_value = 9901
    yield window
    G.compiled_rules.pop(window, None)


@pytest.fixture
def created_views(monkeypatch):
    """Record the views the commands would open instead of opening them."""
    created: list[dict] = []
    for mod in (debug_mod, summary_mod):
        monkeypatch.setattr(mod, "create_new_view", lambda **kwargs: created.append(kwargs))
    return created


class TestDebugInformation:
    def test_report_has_every_section_and_opens_as_python(self, window, created_views, monkeypatch):
        monkeypatch.setattr(debug_mod, "get_merged_plugin_settings", lambda **kw: {"enable_log": True})

        debug_mod.AutoSetSyntaxDebugInformationCommand(window).run()

        (view,) = created_views
        assert view["syntax"] == "scope:source.python"
        assert view["scratch"] is True
        for section in ("Environment", "Plugin settings", "Syntax rule collection", "Dropped syntax rules"):
            assert section in view["content"]
        assert "enable_log" in view["content"]

    def test_dropped_rules_are_listed_with_the_reason_they_were_dropped(self, window, created_views, monkeypatch):
        monkeypatch.setattr(debug_mod, "get_merged_plugin_settings", lambda **kw: {})
        G.compiled_rules[window] = CompiledRules(
            MagicMock(), [DroppedRule("never matches: no extension was given", "a rule")]
        )

        debug_mod.AutoSetSyntaxDebugInformationCommand(window).run()

        assert "no extension was given" in created_views[0]["content"]

    def test_a_window_without_compiled_rules_still_reports(self, window, created_views, monkeypatch):
        monkeypatch.setattr(debug_mod, "get_merged_plugin_settings", lambda **kw: {})

        debug_mod.AutoSetSyntaxDebugInformationCommand(window).run()

        assert len(created_views) == 1

    def test_environment_lists_the_known_constraints_and_matches(self, window, created_views, monkeypatch):
        import plugin.rules  # ruff:ignore[unused-import]

        monkeypatch.setattr(debug_mod, "get_merged_plugin_settings", lambda **kw: {})

        debug_mod.AutoSetSyntaxDebugInformationCommand(window).run()

        content = created_views[0]["content"]
        assert "IsExtensionConstraint" in content
        assert "AnyMatch" in content


def _compiled_rule(syntax: sublime.Syntax | None, **setting) -> MagicMock:
    rule = MagicMock()
    rule.syntax = syntax
    rule.src_setting = StSyntaxRule(**setting)
    return rule


class TestSyntaxRulesSummary:
    def test_no_compiled_rules_opens_nothing(self, window, created_views):
        summary_mod.AutoSetSyntaxSyntaxRulesSummaryCommand(window).run()

        assert created_views == []

    def test_rules_are_grouped_under_their_syntax_sorted_by_name(self, window, created_views):
        python = sublime.Syntax("Packages/Python/Python.sublime-syntax", "Python", False, "source.python")
        json = sublime.Syntax("Packages/JSON/JSON.sublime-syntax", "JSON", False, "source.json")
        collection = MagicMock()
        collection.rules = (
            _compiled_rule(python, comment="first python"),
            _compiled_rule(json, comment="a json"),
            _compiled_rule(python, comment="second python"),
        )
        G.compiled_rules[window] = CompiledRules(collection, [])

        summary_mod.AutoSetSyntaxSyntaxRulesSummaryCommand(window).run()

        content = created_views[0]["content"]
        assert content.index("// Syntax : JSON") < content.index("// Syntax : Python")
        assert content.count("// Syntax : Python") == 1
        assert content.index("// Syntax : Python") < content.index("first python") < content.index("second python")

    def test_a_rule_without_a_resolved_syntax_is_left_out(self, window, created_views):
        python = sublime.Syntax("Packages/Python/Python.sublime-syntax", "Python", False, "source.python")
        collection = MagicMock()
        collection.rules = (_compiled_rule(None, comment="unresolved"), _compiled_rule(python, comment="resolved"))
        G.compiled_rules[window] = CompiledRules(collection, [])

        summary_mod.AutoSetSyntaxSyntaxRulesSummaryCommand(window).run()

        content = created_views[0]["content"]
        assert "resolved" in content
        assert "unresolved" not in content

    def test_the_summary_opens_as_jsonc_using_a_hidden_syntax(self, window, created_views):
        python = sublime.Syntax("Packages/Python/Python.sublime-syntax", "Python", False, "source.python")
        collection = MagicMock()
        collection.rules = (_compiled_rule(python),)
        G.compiled_rules[window] = CompiledRules(collection, [])

        summary_mod.AutoSetSyntaxSyntaxRulesSummaryCommand(window).run()

        view = created_views[0]
        assert view["syntax"] == "scope:source.autosetsyntax.jsonc"
        assert view["include_hidden_syntax"] is True
