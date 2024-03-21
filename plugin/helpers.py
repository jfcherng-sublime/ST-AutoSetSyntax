from __future__ import annotations

from collections import deque

import sublime

from .settings import get_st_setting
from .utils import is_plaintext_syntax, is_transient_view


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
