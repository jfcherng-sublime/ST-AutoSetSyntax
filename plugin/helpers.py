from __future__ import annotations

import sublime

from .settings import get_st_setting
from .utils import is_plaintext_syntax, is_transient_view, stable_unique


def is_syntaxable_view(view: sublime.View, must_plaintext: bool = False) -> bool:
    """Determinates whether the view is what we want to set a syntax on."""
    return bool(
        view.is_valid()
        and not view.element()
        and not is_transient_view(view)
        and (not must_plaintext or ((syntax := view.syntax()) and is_plaintext_syntax(syntax)))
        and ((size_max := get_st_setting("syntax_detection_size_limit", 0)) == 0 or size_max >= view.size())
    )


def resolve_magika_label_with_syntax_map(label: str, syntax_map: dict[str, list[str]]) -> list[str]:
    res: list[str] = []
    queue: list[str] = syntax_map.get(label, []).copy()

    # @todo what if there are circular references?
    while queue:
        syntax_like = queue.pop()
        if syntax_like.startswith("="):
            queue.extend(syntax_map.get(syntax_like[1:], []))
            continue
        res.append(syntax_like)

    return list(stable_unique(reversed(res)))
