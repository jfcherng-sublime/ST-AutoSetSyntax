"""Tests for plugin/helpers.py -- previously zero dedicated coverage."""

from unittest.mock import MagicMock

import sublime

import plugin.helpers as mod


def _make_view(
    *,
    valid: bool = True,
    element: str | None = None,
    transient: bool = False,
    syntax: sublime.Syntax | None = None,
    size: int = 100,
) -> MagicMock:
    view = MagicMock()
    view.is_valid.return_value = valid
    view.element.return_value = element
    view.syntax.return_value = syntax
    view.size.return_value = size
    view.sheet.return_value = MagicMock(is_transient=MagicMock(return_value=transient))
    return view


class TestIsSyntaxableView:
    def test_invalid_view_rejected(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(valid=False)
        assert mod.is_syntaxable_view(view) is False

    def test_widget_element_rejected(self, monkeypatch):
        """`element()` is non-None/non-empty for special views (find panels, quick-input
        widgets, etc.) which must never get an automatic syntax reassignment."""
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(element="find_input")
        assert mod.is_syntaxable_view(view) is False

    def test_transient_view_rejected(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(transient=True)
        assert mod.is_syntaxable_view(view) is False

    def test_plain_view_accepted_by_default(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view()
        assert mod.is_syntaxable_view(view) is True

    def test_must_plaintext_rejects_non_plaintext_syntax(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(syntax=sublime.Syntax(name="Python"))
        assert mod.is_syntaxable_view(view, must_plaintext=True) is False

    def test_must_plaintext_accepts_plaintext_syntax(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        assert mod.is_syntaxable_view(view, must_plaintext=True) is True

    def test_must_plaintext_false_ignores_current_syntax(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(syntax=sublime.Syntax(name="Python"))
        assert mod.is_syntaxable_view(view, must_plaintext=False) is True

    def test_zero_size_limit_means_unlimited(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 0)
        view = _make_view(size=10_000_000)
        assert mod.is_syntaxable_view(view) is True

    def test_view_over_size_limit_rejected(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 1000)
        view = _make_view(size=2000)
        assert mod.is_syntaxable_view(view) is False

    def test_view_within_size_limit_accepted(self, monkeypatch):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 1000)
        view = _make_view(size=500)
        assert mod.is_syntaxable_view(view) is True

    def test_view_exactly_at_size_limit_accepted(self, monkeypatch):
        """The boundary is inclusive (`size_max >= view.size()`)."""
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: 1000)
        view = _make_view(size=1000)
        assert mod.is_syntaxable_view(view) is True


class TestCreateNewView:
    def test_creates_view_with_name_and_content(self):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view

        result = mod.create_new_view(name="My View", content="hello", window=window)

        assert result is new_view
        new_view.set_name.assert_called_once_with("My View")
        new_view.run_command.assert_called_once_with("append", {"characters": "hello"})

    def test_marks_view_as_created(self):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        settings_obj = MagicMock()
        new_view.settings.return_value = settings_obj

        mod.create_new_view(window=window)

        updated = settings_obj.update.call_args[0][0]
        assert updated[mod.VIEW_KEY_IS_CREATED] is True

    def test_user_settings_are_preserved_alongside_created_marker(self):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        settings_obj = MagicMock()
        new_view.settings.return_value = settings_obj

        mod.create_new_view(window=window, settings={"tab_size": 2})

        updated = settings_obj.update.call_args[0][0]
        assert updated["tab_size"] == 2
        assert updated[mod.VIEW_KEY_IS_CREATED] is True

    def test_syntax_assigned_when_resolvable(self, monkeypatch):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        resolved = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: resolved)

        mod.create_new_view(window=window, syntax="scope:source.python")

        new_view.assign_syntax.assert_called_once_with(resolved)

    def test_syntax_not_assigned_when_unresolvable(self, monkeypatch):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: None)

        mod.create_new_view(window=window, syntax="not-a-real-syntax")

        new_view.assign_syntax.assert_not_called()

    def test_no_syntax_arg_skips_lookup_entirely(self, monkeypatch):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        called = []
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: called.append(1))

        mod.create_new_view(window=window)

        assert called == []
        new_view.assign_syntax.assert_not_called()
