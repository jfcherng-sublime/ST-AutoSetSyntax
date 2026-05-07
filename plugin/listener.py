from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from functools import wraps
from typing import Any

import sublime
import sublime_plugin

from .commands.auto_set_syntax import run_auto_set_syntax_on_view
from .constants import PLUGIN_NAME
from .constants import PY_VERSION
from .constants import ST_CHANNEL
from .constants import ST_PLATFORM_ARCH
from .constants import ST_VERSION
from .constants import VERSION
from .constants import VIEW_KEY_IS_TRANSIENT
from .helpers import is_syntaxable_view
from .logger import Logger
from .magika import get_magika_object
from .rules import SyntaxRuleCollection
from .rules import get_constraints
from .rules import get_matches
from .settings import get_merged_plugin_setting
from .settings import pref_syntax_rules
from .shared import G
from .types import ListenerEvent
from .utils import debounce
from .utils import is_transient_view
from .utils import stringify


def set_up_window(window: sublime.Window) -> None:
    Logger.log(f"🤠 Howdy! This is {PLUGIN_NAME} {VERSION}. (Panel for {window})", window=window)
    Logger.log(
        f"🌱 Environment: ST {ST_VERSION} {ST_CHANNEL} build with Python {PY_VERSION} ({ST_PLATFORM_ARCH})",
        window=window,
    )
    if magika_obj := get_magika_object():
        Logger.log(
            f"🔮 Magika is available. (v{magika_obj.get_module_version()} / {magika_obj.get_model_name()})",
            window=window,
        )
    compile_rules(window)
    Logger.log("🎉 Plugin is ready now!", window=window)


def tear_down_window(window: sublime.Window) -> None:
    G.syntax_rule_collections.pop(window, None)
    G.dropped_rules_collection.pop(window, None)
    Logger.log("👋 Bye!", window=window)
    Logger.destroy(window=window)


def compile_rules(window: sublime.Window, *, is_update: bool = False) -> None:
    def names_as_str(items: Iterable[Any], *, sep: str = ", ") -> str:
        return sep.join(item.name() for item in items)

    Logger.log(
        f"# {Logger.DELIMITER} re-compile rules for {window} {Logger.DELIMITER} BEGIN",
        window=window,
        enabled=is_update,
    )

    Logger.log(f'🔍 Found "Match" implementations: {names_as_str(get_matches())}', window=window)
    Logger.log(f'🔍 Found "Constraint" implementations: {names_as_str(get_constraints())}', window=window)

    syntax_rule_collection = SyntaxRuleCollection.make(pref_syntax_rules(window=window))
    G.syntax_rule_collections[window] = syntax_rule_collection
    Logger.log(f"📜 Compiled syntax rule collection: {stringify(syntax_rule_collection)}", window=window)

    dropped_rules = list(syntax_rule_collection.optimize())
    G.dropped_rules_collection[window] = dropped_rules
    Logger.log(f"✨ Optimized syntax rule collection: {stringify(syntax_rule_collection)}", window=window)
    Logger.log(f"💀 Dropped rules during optimizing: {stringify(dropped_rules)}", window=window)

    Logger.log(
        f"# {Logger.DELIMITER} re-compile rules for {window} {Logger.DELIMITER} END",
        window=window,
        enabled=is_update,
    )


def _configured_debounce[T: Callable](func: T) -> T:
    """Debounce a function so that it's called once in seconds."""
    _cache: dict[float, Any] = {}

    def debounced(*args: Any, **kwargs: Any) -> Any:
        if (time_s := get_merged_plugin_setting("debounce", 0)) > 0:
            if time_s not in _cache:
                _cache.clear()  # discard stale wrapper when time_s changes
                _cache[time_s] = debounce(time_s)(func)
            return _cache[time_s](*args, **kwargs)
        return func(*args, **kwargs)

    return debounced  # type: ignore[return-value]


def _guarantee_primary_view[T: Callable](*, must_plaintext: bool = False) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapped(self: sublime_plugin.TextChangeListener, *args: Any, **kwargs: Any) -> None:
            if (
                self.buffer
                and (view := self.buffer.primary_view())
                and view.id()  # workaround for async listener
                and is_syntaxable_view(view, must_plaintext=must_plaintext)
            ):
                func(self, view, *args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorator


class AutoSetSyntaxTextChangeListener(sublime_plugin.TextChangeListener):
    @_guarantee_primary_view()
    def on_revert(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.REVERT)

    @_guarantee_primary_view(must_plaintext=True)
    def on_text_changed_async(self, view: sublime.View, changes: list[sublime.TextChange]) -> None:
        _try_assign_syntax_when_text_changed(view, changes)


class AutoSetSyntaxEventListener(sublime_plugin.EventListener):
    def on_activated(self, view: sublime.View) -> None:
        _try_assign_syntax_when_view_untransientize(view)

    def on_init(self, views: list[sublime.View]) -> None:
        G.startup_views |= set(views)

    def on_load(self, view: sublime.View) -> None:
        view.settings().set(VIEW_KEY_IS_TRANSIENT, is_transient_view(view))
        run_auto_set_syntax_on_view(view, ListenerEvent.LOAD)

    def on_load_project(self, window: sublime.Window) -> None:
        # how to prevent new project views from triggering on_load()?
        # the `window` at this moment has no view in it
        pass

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

    def on_post_window_command(self, window: sublime.Window, command_name: str, args: dict[str, Any]) -> None:
        if command_name in ("build", "exec") and (view := window.find_output_panel("exec")):
            run_auto_set_syntax_on_view(view, ListenerEvent.EXEC)


@_configured_debounce
def _try_assign_syntax_when_text_changed(view: sublime.View, changes: Sequence[sublime.TextChange]) -> bool:
    # don't use `len(changes) <= 1` here because it has a length of 3
    # for `view.run_command('insert', {'characters': 'foo\nbar'})` and that's unwanted
    if len(view.sel()) != 1:
        return False

    # paste = added change is too large
    if sum(len(change.str) for change in changes) >= 8:
        return run_auto_set_syntax_on_view(view, ListenerEvent.PASTE, must_plaintext=True)

    v_size = view.size()
    historic_position = changes[0].b
    if (
        # content is short
        v_size <= 300
        # editing the first line
        or historic_position.row == 0
        # editing last few chars
        or historic_position.pt >= v_size - 2
    ):
        return run_auto_set_syntax_on_view(view, ListenerEvent.MODIFY, must_plaintext=True)
    return False


def _try_assign_syntax_when_view_untransientize(view: sublime.View) -> bool:
    if (settings := view.settings()).get(VIEW_KEY_IS_TRANSIENT):
        settings.erase(VIEW_KEY_IS_TRANSIENT)
        return run_auto_set_syntax_on_view(view, ListenerEvent.UNTRANSIENTIZE)
    return False
