from typing import Any
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..constants import VIEW_KEY_IS_ASSIGNED
from ..detectors import SyntaxDecision
from ..detectors import detect
from ..detectors import detect_for_exec_output
from ..detectors import detect_for_new_view
from ..helpers import is_syntaxable_view
from ..logger import Logger
from ..settings import get_merged_plugin_settings
from ..shared import G
from ..snapshot import ViewSnapshot
from ..types import NULL_SYNTAX
from ..types import ListenerEvent
from ..utils import get_syntax_name
from ..utils import stringify


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    @override
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    @override
    def run(self, edit: sublime.Edit) -> None:
        run_auto_set_syntax_on_view(self.view, ListenerEvent.COMMAND, must_plaintext=False)


def run_auto_set_syntax_on_view(
    view: sublime.View,
    event: ListenerEvent | None = None,
    *,
    must_plaintext: bool = False,
) -> bool:
    if not ((window := view.window()) and G.is_plugin_ready(window) and view.is_valid()):
        Logger.log("⏳ Calm down! View has gone or the plugin is not ready yet.")
        return False

    settings = get_merged_plugin_settings(window=window)

    if event is ListenerEvent.EXEC:
        return _apply(view, detect_for_exec_output(view, event, settings))

    if not (
        is_syntaxable_view(view, must_plaintext=must_plaintext)
        # `is not None`, not truthiness: an empty collection still lets the non-rule detectors run
        and (syntax_rule_collection := G.syntax_rule_collections.get(window)) is not None
    ):
        return False

    view_snapshot = ViewSnapshot.from_view(view)

    if event is ListenerEvent.NEW:
        return _apply(view, detect_for_new_view(view_snapshot, event, settings))

    if decision := detect(view_snapshot, syntax_rule_collection, event, settings):
        return _apply(view, decision)

    return _sorry_cannot_help(view, event)


def _apply(view: sublime.View, decision: SyntaxDecision | None) -> bool:
    """Carry out a `decision`. The only place a detector's verdict reaches the view."""
    if not decision:
        return False
    if decision.status_message:
        sublime.status_message(decision.status_message)
    return assign_syntax_to_view(view, decision.syntax, details=decision.details)


def _sorry_cannot_help(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    details: dict[str, Any] = {"event": event, "reason": "no matching rule"}
    Logger.log(lambda: f"❌ Cannot help {stringify(view)} because {stringify(details)}", window=view.window())
    return False


def assign_syntax_to_view(
    view: sublime.View,
    syntax: sublime.Syntax,
    *,
    details: dict[str, Any] | None = None,
) -> bool:
    if not view.is_valid():
        return False

    details = {**(details or {}), "syntax": syntax}

    for view_ in view.buffer().views():
        if not (window := view_.window()):
            continue

        if syntax == (syntax_old := view_.syntax() or NULL_SYNTAX):
            # use lambda for lazy evaluation: stringify is skipped if logging is off
            Logger.log(
                lambda d=details, s=syntax, v=view_: (  # type: ignore[misc]
                    f'💯 Remain {stringify(v)} syntax "{get_syntax_name(s)}"'
                    f" because {stringify({**d, 'reason': f'[ALREADY] {d["reason"]}'})}"
                ),
                window=window,
            )
            continue

        view_.assign_syntax(syntax)
        view_.settings().set(VIEW_KEY_IS_ASSIGNED, True)
        Logger.log(
            lambda d=details, s=syntax, so=syntax_old, v=view_: (  # type: ignore[misc]
                f"✔ Change {stringify(v)} syntax"
                f' from "{get_syntax_name(so)}" to "{get_syntax_name(s)}"'
                f" because {stringify(d)}"
            ),
            window=window,
        )

    return True
