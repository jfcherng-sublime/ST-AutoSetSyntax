from typing import Callable, Optional
import sublime

# available as of ST 4114
_view_clear_undo_stack: Optional[Callable[[sublime.View], None]] = getattr(sublime.View, "clear_undo_stack")


def view_clear_undo_stack(view: sublime.View) -> None:
    if _view_clear_undo_stack:
        _view_clear_undo_stack(view)
