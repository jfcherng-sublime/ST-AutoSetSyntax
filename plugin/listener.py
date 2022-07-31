from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence

import sublime
import sublime_plugin

from .commands.auto_set_syntax import run_auto_set_syntax_on_view
from .constant import (
    PLUGIN_NAME,
    PY_VERSION,
    ST_CHANNEL,
    ST_PLATFORM_ARCH,
    ST_VERSION,
    VERSION,
    VIEW_IS_TRANSIENT_SETTINGS_KEY,
)
from .guesslang.server import GuesslangServer
from .helper import debounce, is_syntaxable_view, is_transient_view, stringify
from .logger import Logger
from .rules import SyntaxRuleCollection, get_constraints, get_matches
from .settings import pref_syntax_rules
from .shared import G
from .types import ListenerEvent


def set_up_window(window: sublime.Window) -> None:
    Logger.log(window, f"🤠 Howdy! This is {PLUGIN_NAME} {VERSION}. (Panel for {window})")
    Logger.log(
        window,
        f"🌱 Environment: ST {ST_VERSION} ({ST_PLATFORM_ARCH} {ST_CHANNEL} build) with Python {PY_VERSION}",
    )
    compile_rules(window)
    Logger.log(window, "🎉 Plugin is ready now!")


def tear_down_window(window: sublime.Window) -> None:
    G.remove_syntax_rule_collection(window)
    G.remove_dropped_rules(window)
    Logger.log(window, "👋 Bye!")
    Logger.destroy(window)


def compile_rules(window: sublime.Window, is_update: bool = False) -> None:
    delimiter = "-" * 10

    Logger.log(
        window,
        f"# {delimiter} re-compile rules for {window} {delimiter} BEGIN",
        enabled=is_update,
    )

    Logger.log(window, f'🔍 Found "Match" implementations: {stringify(get_matches())}')
    Logger.log(window, f'🔍 Found "Constraint" implementations: {stringify(get_constraints())}')

    syntax_rule_collection = SyntaxRuleCollection.make(pref_syntax_rules(window=window))
    G.set_syntax_rule_collection(window, syntax_rule_collection)
    Logger.log(window, f"📜 Compiled syntax rule collection: {stringify(syntax_rule_collection)}")

    dropped_rules = tuple(syntax_rule_collection.optimize())
    G.set_dropped_rules(window, dropped_rules)
    Logger.log(window, f"✨ Optimized syntax rule collection: {stringify(syntax_rule_collection)}")
    Logger.log(window, f"💀 Dropped rules during optimizing: {stringify(dropped_rules)}")

    Logger.log(
        window,
        f"# {delimiter} re-compile rules for {window} {delimiter} END",
        enabled=is_update,
    )


def _guarantee_primary_view(func: Callable) -> Callable:
    def wrapped(self: sublime_plugin.TextChangeListener, *args: Any, **kwargs: Any) -> None:
        # view.id() is a workaround for async listener
        if self.buffer and (view := self.buffer.primary_view()) and view.id() and is_syntaxable_view(view):
            func(self, view, *args, **kwargs)

    return wrapped


class AutoSetSyntaxTextChangeListener(sublime_plugin.TextChangeListener):
    @_guarantee_primary_view
    def on_revert(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.REVERT)

    @_guarantee_primary_view
    def on_text_changed_async(self, view: sublime.View, changes: List[sublime.TextChange]) -> None:
        _try_assign_syntax_when_text_changed(view, changes)


class AutoSetSyntaxEventListener(sublime_plugin.EventListener):
    def on_exit(self) -> None:
        GuesslangServer.stop()

    def on_activated(self, view: sublime.View) -> None:
        _try_assign_syntax_when_view_untransientize(view)

    def on_init(self, views: List[sublime.View]) -> None:
        G.views_on_init = tuple(views)

    def on_load(self, view: sublime.View) -> None:
        view.settings().set(VIEW_IS_TRANSIENT_SETTINGS_KEY, is_transient_view(view))
        run_auto_set_syntax_on_view(view, ListenerEvent.LOAD)

    def on_load_project(self, window: sublime.Window) -> None:
        # how to prevent new project views from triggering on_load()?
        # the `window` at this moment has no view in it
        ...

    def on_new(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.NEW)

    def on_new_window(self, window: sublime.Window) -> None:
        set_up_window(window)

    def on_post_save(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.SAVE)

    def on_pre_close_window(self, window: sublime.Window) -> None:
        tear_down_window(window)

    def on_reload(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.RELOAD)

    def on_post_window_command(self, window: sublime.Window, command_name: str, args: Dict[str, Any]) -> None:
        if command_name in ("build", "exec") and (view := window.find_output_panel("exec")):
            run_auto_set_syntax_on_view(view, ListenerEvent.EXEC)


@debounce()
def _try_assign_syntax_when_text_changed(view: sublime.View, changes: Sequence[sublime.TextChange]) -> bool:
    # don't use `len(changes) <= 1` here because it has a length of 3
    # for `view.run_command('insert', {'characters': 'foo\nbar'})` and that's unwanted
    if len(view.sel()) != 1:
        return False

    # paste = added change is too large
    if len(changes) == 1 and len(changes[0].str) >= 5:
        return run_auto_set_syntax_on_view(view, ListenerEvent.PASTE, must_plaintext=True)

    historic_position = changes[0].b
    if (
        # content is short
        view.size() <= 300
        # editing the first line
        or historic_position.row == 0
        # editing last few chars
        or historic_position.pt >= view.size() - 2
    ):
        return run_auto_set_syntax_on_view(view, ListenerEvent.MODIFY, must_plaintext=True)
    return False


def _try_assign_syntax_when_view_untransientize(view: sublime.View) -> bool:
    if (settings := view.settings()).get(VIEW_IS_TRANSIENT_SETTINGS_KEY):
        settings.erase(VIEW_IS_TRANSIENT_SETTINGS_KEY)
        return run_auto_set_syntax_on_view(view, ListenerEvent.UNTRANSIENTIZE)
    return False
