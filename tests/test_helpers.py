"""Tests for plugin/helpers.py -- previously zero dedicated coverage."""

from unittest.mock import MagicMock

import pytest
import sublime

import plugin.helpers as mod

PYTHON = sublime.Syntax(name="Python")
PLAIN = sublime.Syntax(name="Plain Text")


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
    @pytest.mark.parametrize(
        ("view_kwargs", "kwargs", "size_max", "expected"),
        [
            pytest.param({"valid": False}, {}, 0, False, id="invalid"),
            # `element()` is non-None for special views (find panels, quick-input widgets, ...)
            pytest.param({"element": "find_input"}, {}, 0, False, id="widget"),
            pytest.param({"transient": True}, {}, 0, False, id="transient"),
            pytest.param({}, {}, 0, True, id="plain"),
            pytest.param({"syntax": PYTHON}, {"must_plaintext": True}, 0, False, id="plaintext-required-got-python"),
            pytest.param({"syntax": PLAIN}, {"must_plaintext": True}, 0, True, id="plaintext-required-got-plain"),
            pytest.param({"syntax": PYTHON}, {"must_plaintext": False}, 0, True, id="plaintext-not-required"),
            pytest.param({"size": 10_000_000}, {}, 0, True, id="zero-limit-is-unlimited"),
            pytest.param({"size": 2000}, {}, 1000, False, id="over-limit"),
            pytest.param({"size": 500}, {}, 1000, True, id="under-limit"),
            pytest.param({"size": 1000}, {}, 1000, True, id="exactly-at-limit"),
        ],
    )
    def test_verdict(self, monkeypatch, view_kwargs, kwargs, size_max, expected):
        monkeypatch.setattr(mod, "get_st_setting", lambda *a, **kw: size_max)

        assert mod.is_syntaxable_view(_make_view(**view_kwargs), **kwargs) is expected


class TestCreateNewView:
    def test_creates_view_with_name_and_content(self):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view

        result = mod.create_new_view(name="My View", content="hello", window=window)

        assert result is new_view
        new_view.set_name.assert_called_once_with("My View")
        new_view.run_command.assert_called_once_with("append", {"characters": "hello"})

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
        monkeypatch.setattr(mod, "find_syntax", lambda *a, **kw: resolved)

        mod.create_new_view(window=window, syntax="scope:source.python")

        new_view.assign_syntax.assert_called_once_with(resolved)

    def test_syntax_not_assigned_when_unresolvable(self, monkeypatch):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        monkeypatch.setattr(mod, "find_syntax", lambda *a, **kw: None)

        mod.create_new_view(window=window, syntax="not-a-real-syntax")

        new_view.assign_syntax.assert_not_called()

    def test_no_syntax_arg_skips_lookup_entirely(self, monkeypatch):
        window = MagicMock()
        new_view = MagicMock()
        window.new_file.return_value = new_view
        called = []
        monkeypatch.setattr(mod, "find_syntax", lambda *a, **kw: called.append(1))

        mod.create_new_view(window=window)

        assert called == []
        new_view.assign_syntax.assert_not_called()
