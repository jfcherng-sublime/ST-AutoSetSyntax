"""Tests for how Sublime Text events become `ListenerEvent`s (plugin/listener.py)."""

import operator
import time
from unittest.mock import MagicMock

import pytest

import plugin.listener as listener_mod
import plugin.windows as windows_mod
from plugin.constants import VIEW_KEY_IS_TRANSIENT
from plugin.shared import G
from plugin.types import ListenerEvent


@pytest.fixture
def runs(monkeypatch):
    """Record every `run_auto_set_syntax_on_view()` call the listeners make."""
    calls: list[tuple] = []
    monkeypatch.setattr(
        listener_mod,
        "run_auto_set_syntax_on_view",
        lambda view, event, **kwargs: calls.append((view, event, kwargs)) or True,
    )
    return calls


@pytest.fixture
def listener():
    return listener_mod.AutoSetSyntaxEventListener()


class TestEventToListenerEvent:
    @pytest.mark.parametrize(
        ("handler", "expected"),
        [
            ("on_post_save", ListenerEvent.SAVE),
            ("on_reload", ListenerEvent.RELOAD),
        ],
    )
    def test_view_handlers_run_detection_with_their_event(self, listener, runs, handler, expected):
        view = MagicMock()

        getattr(listener, handler)(view)

        assert runs == [(view, expected, {})]

    def test_on_load_runs_detection_and_remembers_whether_the_view_was_transient(self, listener, runs, monkeypatch):
        monkeypatch.setattr(listener_mod, "is_transient_view", lambda view: True)
        view = MagicMock()

        listener.on_load(view)

        view.settings.return_value.set.assert_called_once_with(VIEW_KEY_IS_TRANSIENT, True)
        assert runs == [(view, ListenerEvent.LOAD, {})]


class TestStartupViews:
    def test_on_init_collects_the_views_that_exist_before_the_plugin_loaded(self, listener, monkeypatch):
        monkeypatch.setattr(G, "startup_views", set())
        views = [MagicMock(), MagicMock()]

        listener.on_init(views)

        assert views[0] in G.startup_views
        assert views[1] in G.startup_views


class TestExecOutput:
    @pytest.mark.parametrize("command", ["build", "exec"])
    def test_build_commands_run_detection_on_the_exec_panel(self, listener, runs, command):
        window = MagicMock()

        listener.on_post_window_command(window, command, {})

        assert runs == [(window.find_output_panel.return_value, ListenerEvent.EXEC, {})]

    def test_other_commands_are_ignored(self, listener, runs):
        listener.on_post_window_command(MagicMock(), "save", {})

        assert runs == []

    def test_a_build_without_an_exec_panel_is_ignored(self, listener, runs):
        window = MagicMock()
        window.find_output_panel.return_value = None

        listener.on_post_window_command(window, "build", {})

        assert runs == []


class TestUntransientize:
    def test_activating_a_view_that_was_transient_runs_detection_once(self, listener, runs):
        view = MagicMock()
        settings = view.settings.return_value
        settings.get.return_value = True

        listener.on_activated(view)

        settings.erase.assert_called_once_with(VIEW_KEY_IS_TRANSIENT)
        assert runs == [(view, ListenerEvent.UNTRANSIENTIZE, {})]

    def test_activating_an_ordinary_view_does_nothing(self, listener, runs):
        view = MagicMock()
        view.settings.return_value.get.return_value = None

        listener.on_activated(view)

        assert runs == []


class TestWindowClose:
    def test_closing_a_window_tears_down_its_rules(self, listener, monkeypatch):
        torn_down = []
        monkeypatch.setattr(listener_mod, "tear_down_window", torn_down.append)
        window = MagicMock()

        listener.on_pre_close_window(window)

        assert torn_down == [window]

    def test_tear_down_forgets_the_windows_compiled_rules(self, monkeypatch):
        window = MagicMock()
        window.id.return_value = 8801
        G.compiled_rules[window] = MagicMock()
        monkeypatch.setattr(windows_mod.Logger, "log", lambda *a, **kw: None)
        monkeypatch.setattr(windows_mod.Logger, "destroy", lambda **kw: None)

        windows_mod.tear_down_window(window)

        assert window not in G.compiled_rules


class TestProjectSettingsSaved:
    def test_refreshes_the_windows_settings(self, listener, monkeypatch):
        refreshed = []
        monkeypatch.setattr(listener_mod.AioSettings, "refresh", refreshed.append)
        window = MagicMock()

        listener.on_load_project_async(window)

        assert refreshed == [window]


class TestDebounce:
    @pytest.fixture
    def record(self, monkeypatch):
        monkeypatch.setattr(listener_mod, "get_merged_plugin_setting", lambda *a, **kw: self.delay)
        calls = []
        self.view1, self.view2 = MagicMock(), MagicMock()
        return listener_mod._configured_debounce(lambda key, value: calls.append((key, value))), calls

    delay = 0.05

    def test_no_delay_runs_immediately(self, record):
        self.delay = 0
        func, calls = record

        func(self.view1, 1)

        assert calls == [(self.view1, 1)]

    def test_runs_once_after_the_delay(self, record):
        func, calls = record

        func(self.view1, "a")
        assert calls == []
        time.sleep(0.2)

        assert calls == [(self.view1, "a")]

    def test_rapid_calls_for_one_key_only_run_the_last(self, record):
        func, calls = record

        for value in (1, 2, 3):
            func(self.view1, value)
        time.sleep(0.2)

        assert calls == [(self.view1, 3)]

    def test_another_key_is_not_cancelled(self, record):
        func, calls = record

        func(self.view1, "a")
        func(self.view2, "b")
        time.sleep(0.2)

        assert sorted(calls, key=operator.itemgetter(1)) == [(self.view1, "a"), (self.view2, "b")]


class TestTextChangeListener:
    @pytest.fixture
    def text_listener(self, monkeypatch):
        view = MagicMock()
        view.id.return_value = 1
        monkeypatch.setattr(listener_mod, "is_syntaxable_view", lambda view, **kw: True)
        instance = listener_mod.AutoSetSyntaxTextChangeListener()
        instance.buffer = MagicMock()
        instance.buffer.primary_view.return_value = view
        return instance, view

    def test_revert_runs_detection_on_the_buffers_primary_view(self, text_listener, runs):
        instance, view = text_listener

        instance.on_revert()

        assert runs == [(view, ListenerEvent.REVERT, {})]

    def test_a_view_that_is_not_syntaxable_is_skipped(self, text_listener, runs, monkeypatch):
        instance, _ = text_listener
        monkeypatch.setattr(listener_mod, "is_syntaxable_view", lambda view, **kw: False)

        instance.on_revert()

        assert runs == []

    def test_a_buffer_whose_view_has_gone_is_skipped(self, text_listener, runs):
        instance, view = text_listener
        view.id.return_value = 0  # an async listener can fire after the view has closed

        instance.on_revert()

        assert runs == []

    def test_text_changes_are_forwarded_with_the_primary_view(self, text_listener, monkeypatch):
        instance, view = text_listener
        forwarded = []
        monkeypatch.setattr(listener_mod, "_try_assign_syntax_when_text_changed", lambda *a: forwarded.append(a))
        changes = [MagicMock()]

        instance.on_text_changed_async(changes)

        assert forwarded == [(view, changes)]


class TestRunOnStartupViews:
    def test_runs_only_for_views_whose_window_enables_it_and_forgets_all(self, monkeypatch):
        enabled_window, disabled_window = MagicMock(), MagicMock()
        enabled, disabled, windowless = MagicMock(), MagicMock(), MagicMock()
        enabled.window.return_value = enabled_window
        disabled.window.return_value = disabled_window
        windowless.window.return_value = None
        ran = []
        monkeypatch.setattr(listener_mod, "get_merged_plugin_setting", lambda key, *, window: window is enabled_window)
        monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda view, event: ran.append(view))
        monkeypatch.setattr(G, "startup_views", {enabled, disabled, windowless})

        listener_mod.run_on_startup_views()

        assert ran == [enabled]
        assert G.startup_views == set()
