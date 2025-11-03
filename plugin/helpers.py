from __future__ import annotations

from collections import deque
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


def resolve_magika_label_with_syntax_map(label: str, syntax_map: dict[str, list[str]]) -> list[str]:
    """
    Resolve a Magika label to a list of syntax like string.

    :param      label:       The syntax label from Magika.
    :param      syntax_map:  The syntax map. Key / value = Maigka label / list of syntax like string.
    """
    # note that dict is insertion-ordered (since Python 3.7)
    res: dict[str, bool] = {}

    deq = deque(syntax_map.get(label, []))
    while deq:
        if (notation := deq.popleft()) in res:
            continue
        res[notation] = False  # visited

        # notation is in the form of "scope:text.xml" or "=xml"
        scope, _, ref = notation.partition("=")

        if ref:
            deq.extendleft(reversed(syntax_map.get(ref, [])))
        else:
            res[scope] = True  # parsed

    return [scope for scope, is_parsed in res.items() if is_parsed]


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
