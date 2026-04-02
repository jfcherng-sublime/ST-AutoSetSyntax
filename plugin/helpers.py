from typing import Any

import sublime

from .constants import VIEW_KEY_IS_CREATED
from .settings import get_st_setting
from .utils import find_syntax_by_syntax_like, is_plaintext_syntax, is_transient_view


def is_syntaxable_view(view: sublime.View, *, must_plaintext: bool = False) -> bool:
    """Determinates whether the view is what we want to set a syntax on."""
    return bool(
        view.is_valid()
        and not view.element()
        and not is_transient_view(view)
        and (not must_plaintext or ((syntax := view.syntax()) and is_plaintext_syntax(syntax)))
        and ((size_max := get_st_setting("syntax_detection_size_limit", 0)) == 0 or size_max >= view.size())
    )


def create_new_view(
    *,
    name: str = "Untitled",
    content: str = "",
    syntax: str | sublime.Syntax | None = None,
    include_hidden_syntax: bool = False,
    scratch: bool = False,
    read_only: bool = False,
    settings: dict[str, Any] | None = None,
    window: sublime.Window | None = None,
) -> sublime.View:
    """Copies the content to a new view."""
    settings = settings or {}
    window = window or sublime.active_window()

    view = window.new_file()
    view.set_name(name)
    view.set_scratch(scratch)
    view.set_read_only(read_only)
    view.settings().update(settings | {VIEW_KEY_IS_CREATED: True})

    if syntax and (syntax := find_syntax_by_syntax_like(syntax, include_hidden=include_hidden_syntax)):
        view.assign_syntax(syntax)

    view.run_command("append", {"characters": content})

    return view
