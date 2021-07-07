from ..constant import PLUGIN_NAME
from ..constant import VIEW_RUN_ID_SETTINGS_KEY
from ..helper import find_syntax_by_syntax_like
from ..helper import generate_trimmed_string
from ..helper import is_plaintext_syntax
from ..helper import is_syntaxable_view
from ..helper import stringify
from ..logger import Logger
from ..rules import SyntaxRuleCollection
from ..settings import get_merged_plugin_setting
from ..settings import pref_trim_suffixes
from ..shared import G
from ..snapshot import ViewSnapshot
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import sublime
import sublime_plugin
import uuid


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    def run(self, edit: sublime.Edit, event_name: str = "command") -> None:
        run_auto_set_syntax_on_view(self.view, event_name)


def _snapshot_view(func: Callable) -> Callable:
    def wrap(view: sublime.View, *args: Any, **kwargs: Any) -> Any:
        run_id = str(uuid.uuid4())
        settings = view.settings()

        settings.set(VIEW_RUN_ID_SETTINGS_KEY, run_id)
        ViewSnapshot.add(run_id, view)
        result = func(view, *args, **kwargs)
        ViewSnapshot.remove(run_id)
        settings.erase(VIEW_RUN_ID_SETTINGS_KEY)

        return result

    return wrap


@_snapshot_view
def run_auto_set_syntax_on_view(
    view: sublime.View,
    event_name: Optional[str] = None,
    must_plaintext=False,
) -> bool:
    if not (window := view.window()) or not is_syntaxable_view(view, must_plaintext):
        return False

    if (syntax_rule_collection := G.get_syntax_rule_collection(window)) is None:
        Logger.log(window, "⏳ Calm down! Plugin is not ready yet.")
        return False

    if event_name == "new":
        return _assign_syntax_for_new_view(view, event_name)

    if _assign_syntax_with_plugin_rules(view, syntax_rule_collection, event_name):
        return True

    if _assign_syntax_with_first_line(view, event_name):
        return True

    if event_name == "load" and _assign_syntax_with_trimmed_filename(view, event_name):
        return True

    return _sorry_cannot_help(view, event_name)


def _assign_syntax_for_new_view(view: sublime.View, event_name: Optional[str] = None) -> bool:
    if (
        (window := view.window())
        and (new_file_syntax := get_merged_plugin_setting(window, "new_file_syntax"))
        and (syntax := find_syntax_by_syntax_like(new_file_syntax, allow_plaintext=False))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event_name, "reason": "new file", "new_file_syntax": new_file_syntax},
        )
    return False


def _assign_syntax_with_plugin_rules(
    view: sublime.View,
    syntax_rule_collection: SyntaxRuleCollection,
    event_name: Optional[str] = None,
) -> bool:
    if syntax_rule := syntax_rule_collection.test(view, event_name):
        assert syntax_rule.syntax  # otherwise it should be dropped during optimizing
        return assign_syntax_to_view(
            view,
            syntax_rule.syntax,
            details={"event": event_name, "reason": "plugin rule", "rule": syntax_rule},
        )
    return False


def _assign_syntax_with_first_line(view: sublime.View, event_name: Optional[str] = None) -> bool:
    if (
        (view_info := ViewSnapshot.get_by_view(view))
        and (syntax := sublime.find_syntax_for_file("", view_info["first_line"]))
        and not is_plaintext_syntax(syntax)
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event_name, "reason": 'syntax "first_line_match"'},
        )
    return False


def _assign_syntax_with_trimmed_filename(view: sublime.View, event_name: Optional[str] = None) -> bool:
    if not (filepath := view.file_name()) or not (window := view.window()):
        return False

    suffixes = pref_trim_suffixes(window)
    for trimmed in generate_trimmed_string((original := Path(filepath).name), suffixes):
        if (syntax := sublime.find_syntax_for_file(trimmed)) and not is_plaintext_syntax(syntax):
            return assign_syntax_to_view(
                view,
                syntax,
                details={
                    "event": event_name,
                    "reason": "trimmed filename",
                    "filename_original": original,
                    "filename_trimmed": trimmed,
                    "trim_suffixes": suffixes,
                },
            )
    return False


def _sorry_cannot_help(view: sublime.View, event_name: Optional[str] = None) -> bool:
    details = {"event": event_name, "reason": "no matching rule"}
    Logger.log(view.window(), f"❌ Cannot help {stringify(view)} because {stringify(details)}")
    return False


def assign_syntax_to_view(
    view: sublime.View,
    syntax: sublime.Syntax,
    details: Optional[Dict[str, Any]] = None,
    same_buffer: bool = True,
) -> bool:
    if not view.is_valid():
        return False

    details = details or {}
    details["sytnax"] = syntax

    views = view.buffer().views() if same_buffer else (view,)
    for _view in views:
        if not (_window := _view.window()):
            continue

        syntax_old = view.syntax() or sublime.Syntax("", "", False, "")

        if syntax == syntax_old:
            details["reason"] = f'[ALREADY] {details["reason"]}'
            Logger.log(
                _window,
                f'💯 Remain {stringify(_view)} syntax "{syntax.name}" because {stringify(details)}',
            )
            continue

        _view.assign_syntax(syntax)
        Logger.log(
            _window,
            f"✔ Change {stringify(_view)} syntax"
            + f' from "{syntax_old.name}" to "{syntax.name}" because {stringify(details)}',
        )

    return True
