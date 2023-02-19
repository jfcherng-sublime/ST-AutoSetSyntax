import sublime

from .settings import get_st_setting
from .utils import is_plaintext_syntax, is_transient_view


def is_syntaxable_view(view: sublime.View, must_plaintext: bool = False) -> bool:
    """Determinates whether the view is what we want to set a syntax on."""
    return bool(
        view.is_valid()
        and not view.element()
        and not is_transient_view(view)
        and (not must_plaintext or ((syntax := view.syntax()) and is_plaintext_syntax(syntax)))
        and ((size_max := get_st_setting("syntax_detection_size_limit", 0)) == 0 or size_max >= view.size())
    )
