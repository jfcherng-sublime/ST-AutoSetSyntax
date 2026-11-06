from collections.abc import Callable
from collections.abc import Sequence
from functools import lru_cache
from functools import wraps
from typing import Any
from typing import Final
from typing import cast

import sublime
import sublime_plugin

from .commands.auto_set_syntax import run_auto_set_syntax_on_view
from .constants import VIEW_KEY_IS_TRANSIENT
from .helpers import is_syntaxable_view
from .settings import get_merged_plugin_setting
from .shared import G
from .types import ListenerEvent
from .utils import debounce
from .utils import is_transient_view
from .windows import ensure_window_set_up
from .windows import tear_down_window


@lru_cache(maxsize=2)
def _make_debounced[T: Callable](func: T, time_s: float) -> T:
    """
    Cache the debounced wrapper so the same (func, time_s) pair reuses one wrapper.

    The wrapper itself debounces independently per first argument (e.g. per view), so
    reusing it across calls for different views doesn't cancel each other's pending calls.

    ``maxsize=2`` covers the common case (one debounced function with one
    setting-driven delay). Bump when more debounced callbacks are added.
    """
    return debounce(time_s)(func)


def _configured_debounce[T: Callable](func: T) -> T:
    """Debounce a function so that it's called once in seconds."""

    @wraps(func)
    def debounced(*args: Any, **kwargs: Any) -> Any:
        if (time_s := get_merged_plugin_setting("debounce", 0)) > 0:
            return _make_debounced(func, time_s)(*args, **kwargs)
        return func(*args, **kwargs)

    return cast(T, debounced)


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

        return cast(T, wrapped)

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

    def on_new(self, view: sublime.View) -> None:
        if window := view.window():
            ensure_window_set_up(window)
        run_auto_set_syntax_on_view(view, ListenerEvent.NEW)

    def on_new_window(self, window: sublime.Window) -> None:
        ensure_window_set_up(window)

    def on_post_save(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.SAVE)

    def on_pre_close_window(self, window: sublime.Window) -> None:
        tear_down_window(window)

    def on_reload(self, view: sublime.View) -> None:
        run_auto_set_syntax_on_view(view, ListenerEvent.RELOAD)

    def on_post_window_command(self, window: sublime.Window, command_name: str, args: dict[str, Any]) -> None:
        if command_name in ("build", "exec") and (view := window.find_output_panel("exec")):
            run_auto_set_syntax_on_view(view, ListenerEvent.EXEC)


_PASTE_CHANGE_THRESHOLD: Final[int] = 8
"""Minimum total change size to be considered a paste operation."""
_SHORT_CONTENT_THRESHOLD: Final[int] = 300
"""Content size below which any modification triggers re-evaluation."""
_EDIT_END_PROXIMITY: Final[int] = 2
"""Distance from end of content within which edits trigger re-evaluation."""


@_configured_debounce
def _try_assign_syntax_when_text_changed(view: sublime.View, changes: Sequence[sublime.TextChange]) -> bool:
    # don't use `len(changes) <= 1` here because it has a length of 3
    # for `view.run_command('insert', {'characters': 'foo\nbar'})` and that's unwanted
    if len(view.sel()) != 1:
        return False

    # paste = added change is too large
    if sum(len(change.str) for change in changes) >= _PASTE_CHANGE_THRESHOLD:
        return run_auto_set_syntax_on_view(view, ListenerEvent.PASTE, must_plaintext=True)

    v_size = view.size()
    historic_position = changes[0].b
    if (
        # content is short
        v_size <= _SHORT_CONTENT_THRESHOLD
        # editing the first line
        or historic_position.row == 0
        # editing last few chars
        or historic_position.pt >= v_size - _EDIT_END_PROXIMITY
    ):
        return run_auto_set_syntax_on_view(view, ListenerEvent.MODIFY, must_plaintext=True)
    return False


def _try_assign_syntax_when_view_untransientize(view: sublime.View) -> bool:
    if (settings := view.settings()).get(VIEW_KEY_IS_TRANSIENT):
        settings.erase(VIEW_KEY_IS_TRANSIENT)
        return run_auto_set_syntax_on_view(view, ListenerEvent.UNTRANSIENTIZE)
    return False
