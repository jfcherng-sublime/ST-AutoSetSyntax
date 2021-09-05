import sublime


def view_clear_undo_stack(view: sublime.View) -> None:
    """
    Aliased to `view.clear_undo_stack` if possible.

    @version ST(>=4114)
    """
    if clear_undo_stack := getattr(view, "clear_undo_stack", None):
        # this `set_timeout` allows `View.clear_undo_stack` being called in a text command
        sublime.set_timeout(clear_undo_stack)
