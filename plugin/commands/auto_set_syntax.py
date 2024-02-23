from __future__ import annotations

import re
from functools import wraps
from itertools import chain
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, RE_ST_SYNTAX_TEST_LINE, RE_VIM_SYNTAX_LINE
from ..helpers import is_syntaxable_view, resolve_magika_label_with_syntax_map
from ..logger import Logger
from ..rules import SyntaxRuleCollection
from ..settings import get_merged_plugin_setting, get_merged_plugin_settings, pref_trim_suffixes
from ..shared import G
from ..snapshot import ViewSnapshot
from ..types import ListenerEvent
from ..utils import (
    find_syntax_by_syntax_like,
    find_syntax_by_syntax_likes,
    get_syntax_name,
    is_plaintext_syntax,
    list_trimmed_filenames,
    list_trimmed_strings,
    stringify,
)

_T_Callable = TypeVar("_T_Callable", bound=Callable[..., Any])


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    def run(self, edit: sublime.Edit) -> None:
        run_auto_set_syntax_on_view(self.view, ListenerEvent.COMMAND, must_plaintext=False)


def _snapshot_view(failed_ret: Any = None) -> Callable[[_T_Callable], _T_Callable]:
    def decorator(func: _T_Callable) -> _T_Callable:
        @wraps(func)
        def wrapped(view: sublime.View, *args: Any, **kwargs: Any) -> Any:
            if not ((window := view.window()) and G.is_plugin_ready(window) and view.is_valid()):
                Logger.log("⏳ Calm down! View has gone or the plugin is not ready yet.")
                return failed_ret

            with G.view_snapshot_collection.snapshot_context(view):
                return func(view, *args, **kwargs)

        return cast(_T_Callable, wrapped)

    return decorator


@_snapshot_view(failed_ret=False)
def run_auto_set_syntax_on_view(
    view: sublime.View,
    event: ListenerEvent | None = None,
    *,
    must_plaintext: bool = False,
) -> bool:
    if event is ListenerEvent.EXEC:
        return _assign_syntax_for_exec_output(view, event)

    # prerequsites
    if not (
        (window := view.window())
        and is_syntaxable_view(view, must_plaintext=must_plaintext)
        and (syntax_rule_collection := G.syntax_rule_collections.get(window))
    ):
        return False

    if event is ListenerEvent.NEW:
        return _assign_syntax_for_new_view(view, event)

    if _assign_syntax_for_st_syntax_test(view, event):
        return True

    if _assign_syntax_with_plugin_rules(view, syntax_rule_collection, event):
        return True

    if _assign_syntax_with_first_line(view, event):
        return True

    if event in {
        ListenerEvent.COMMAND,
        ListenerEvent.INIT,
        ListenerEvent.LOAD,
        ListenerEvent.SAVE,
        ListenerEvent.UNTRANSIENTIZE,
    } and _assign_syntax_with_trimmed_filename(view, event):
        return True

    if event in {
        ListenerEvent.COMMAND,
        ListenerEvent.INIT,
        ListenerEvent.LOAD,
        ListenerEvent.MODIFY,
        ListenerEvent.PASTE,
        ListenerEvent.SAVE,
        ListenerEvent.UNTRANSIENTIZE,
    } and _assign_syntax_with_magika(view, event):
        return True

    if _assign_syntax_with_heuristics(view, event):
        return True

    return _sorry_cannot_help(view, event)


def _assign_syntax_for_exec_output(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if (
        (window := view.window())
        and (not (syntax_old := view.syntax()) or syntax_old.scope == "text.plain")
        and (exec_file_syntax := get_merged_plugin_setting("exec_file_syntax", window=window))
        and (syntax := find_syntax_by_syntax_like(exec_file_syntax, include_hidden=True))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "exec output", "exec_file_syntax": exec_file_syntax},
        )
    return False


def _assign_syntax_for_new_view(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if (
        (window := view.window())
        and (new_file_syntax := get_merged_plugin_setting("new_file_syntax", window=window))
        and (syntax := find_syntax_by_syntax_like(new_file_syntax, include_plaintext=False))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "new file", "new_file_syntax": new_file_syntax},
        )
    return False


def _assign_syntax_for_st_syntax_test(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if (
        (view_snapshot := G.view_snapshot_collection.get_by_view(view))
        and (not view_snapshot.syntax or is_plaintext_syntax(view_snapshot.syntax))
        and (m := RE_ST_SYNTAX_TEST_LINE.search(view_snapshot.first_line))
        and (new_syntax := m.group("syntax")).endswith(".sublime-syntax")
        and (syntax := find_syntax_by_syntax_like(new_syntax, include_hidden=True, include_plaintext=True))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "Sublime Test syntax test file"},
        )
    return False


def _assign_syntax_with_plugin_rules(
    view: sublime.View,
    syntax_rule_collection: SyntaxRuleCollection,
    event: ListenerEvent | None = None,
) -> bool:
    if syntax_rule := syntax_rule_collection.test(view, event):
        assert syntax_rule.syntax  # otherwise it should be dropped during optimizing
        return assign_syntax_to_view(
            view,
            syntax_rule.syntax,
            details={"event": event, "reason": "plugin rule", "rule": syntax_rule},
        )
    return False


def _assign_syntax_with_first_line(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    # Note that this only works for files under some circumstances.
    # This is to prevent from, for example, changing a ".erb" (Rails HTML template) file into HTML syntax.
    # But we want to change a file whose name is "cpp" with a Python shebang into Python syntax.
    def _prefer_shebang(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        if (
            view_snapshot.first_line.startswith("#!")
            and (syntax := sublime.find_syntax_for_file("", view_snapshot.first_line))
            and not is_plaintext_syntax(syntax)
        ):
            return syntax
        return None

    def _prefer_general_first_line(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        if (
            not view_snapshot.file_extensions
            and (syntax := sublime.find_syntax_for_file(view_snapshot.file_name_unhidden, view_snapshot.first_line))
            and not is_plaintext_syntax(syntax)
        ):
            return syntax
        return None

    def _prefer_vim_modeline(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        for match in RE_VIM_SYNTAX_LINE.finditer(view_snapshot.content):
            if syntax := find_syntax_by_syntax_like(match.group("syntax")):
                return syntax
        return None

    if not (view_snapshot := G.view_snapshot_collection.get_by_view(view)):
        return False

    # It's potentially that a first line of a syntax is a prefix of another syntax's.
    # Thus if the user is typing, only try assigning syntax if this is not triggered by the first line.
    if event is ListenerEvent.MODIFY and view_snapshot.caret_rowcol[0] == 0:
        return False

    for checker in (_prefer_shebang, _prefer_vim_modeline, _prefer_general_first_line):
        if syntax := checker(view_snapshot):
            return assign_syntax_to_view(
                view,
                syntax,
                details={"event": event, "reason": f'syntax "first_line_match" by {checker.__name__}'},
            )

    return False


def _assign_syntax_with_trimmed_filename(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if not (
        (filepath := view.file_name())
        and (window := view.window())
        and (syntax_old := view.syntax())
        and is_plaintext_syntax(syntax_old)
    ):
        return False

    original = Path(filepath).name
    trim_suffixes = pref_trim_suffixes(window=window)
    trim_suffixes_auto = get_merged_plugin_setting("trim_suffixes_auto", window=window)

    filenames = chain(
        list_trimmed_strings(original, trim_suffixes, skip_self=True),
        list_trimmed_filenames(original, skip_self=True) if trim_suffixes_auto else tuple(),
    )

    for filename in filenames:
        if (syntax := sublime.find_syntax_for_file(filename)) and not is_plaintext_syntax(syntax):
            return assign_syntax_to_view(
                view,
                syntax,
                details={
                    "event": event,
                    "reason": "trimmed filename",
                    "filename_original": original,
                    "filename_trimmed": filename,
                    "trim_suffixes": trim_suffixes,
                    "trim_suffixes_auto": trim_suffixes_auto,
                },
            )
    return False


def _assign_syntax_with_heuristics(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if not (
        (view_snapshot := G.view_snapshot_collection.get_by_view(view))
        and view_snapshot.syntax
        and is_plaintext_syntax(view_snapshot.syntax)
    ):
        return False

    def is_large_file(view: sublime.View) -> bool:
        return view.size() >= 10 * 1024  # 10KB

    def is_json(view: sublime.View) -> bool:
        view_snapshot = G.view_snapshot_collection.get_by_view(view)
        assert view_snapshot

        text_begin = re.sub(r"\s+", "", view_snapshot.content[:10])
        text_end = re.sub(r"\s+", "", view_snapshot.content[-10:])

        # XSSI protection prefix (https://security.stackexchange.com/q/110539)
        if text_begin.startswith((")]}'\n", ")]}',\n")):
            return True

        return is_large_file(view) and bool(
            # map
            (re.search(r'^\{"', text_begin) and re.search(r'(?:[\d"\]}]|true|false|null)\}$', text_end))
            # array
            or (re.search(r'^\["', text_begin) and re.search(r'(?:[\d"\]}]|true|false|null)\]$', text_end))
            or (text_begin.startswith("[[") and text_end.endswith("]]"))
            or (text_begin.startswith("[{") and text_end.endswith("}]"))
        )

    if is_json(view) and (syntax := find_syntax_by_syntax_like("scope:source.json")):
        return assign_syntax_to_view(view, syntax, details={"event": event, "reason": "heuristics"})

    return False


def _assign_syntax_with_magika(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if not (
        (window := view.window())
        and (settings := get_merged_plugin_settings(window=window))
        and settings.get("magika.enabled")
        and (view_snapshot := G.view_snapshot_collection.get_by_view(view))
        # don't apply on those have an extension
        and (event == ListenerEvent.COMMAND or "." not in view_snapshot.file_name_unhidden)
        # only apply on plain text syntax
        and ((syntax := view_snapshot.syntax) and is_plaintext_syntax(syntax))
        # we don't want to use AI model during typing when there is only one line
        # that may result in unwanted behavior such as a new buffer may be assigned to Python
        # right after "import" is typed but it could be JavaScript or TypeScript as well
        and (event != ListenerEvent.MODIFY or "\n" in view_snapshot.content)
    ):
        return False

    try:
        from magika import Magika
    except ImportError as e:
        Logger.log(f"💣 Error occured when importing Magika: {e}", window=window)
        return False

    classifier = Magika()
    output = classifier.identify_bytes(view_snapshot.content.encode()).output
    Logger.log(f"🐛 Magika's prediction: {output}", window=window)

    threadshold: float = settings.get("magika.min_confidence", 0.0)
    if output.score < threadshold or output.ct_label in {"directory", "empty", "txt", "unknown"}:
        return False

    syntax_map: dict[str, list[str]] = settings.get("magika.syntax_map", {})
    if not (syntax_likes := resolve_magika_label_with_syntax_map(output.ct_label, syntax_map)):
        Logger.log(f'🤔 Unknown "label" from Magika: {output.ct_label}', window=window)
        return False

    if not (syntax := find_syntax_by_syntax_likes(syntax_likes, include_plaintext=False)):
        Logger.log(f"😢 Failed finding syntax from Magika: {syntax_likes}", window=window)
        return False

    sublime.status_message(f"Predicted syntax: {output.ct_label} ({round(output.score * 100, 2)}% confidence)")
    return assign_syntax_to_view(view, syntax, details={"event": event, "reason": "Magika (Deep Learning)"})


def _sorry_cannot_help(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    details = {"event": event, "reason": "no matching rule"}
    Logger.log(f"❌ Cannot help {stringify(view)} because {stringify(details)}", window=view.window())
    return False


def assign_syntax_to_view(
    view: sublime.View,
    syntax: sublime.Syntax,
    *,
    details: dict[str, Any] | None = None,
    same_buffer: bool = True,
) -> bool:
    if not view.is_valid():
        return False

    details = details or {}
    details["syntax"] = syntax

    _views = view.buffer().views() if same_buffer else (view,)
    for _view in _views:
        if not (_window := _view.window()):
            continue

        if syntax == (syntax_old := view.syntax() or sublime.Syntax("", "", False, "")):
            details["reason"] = f'[ALREADY] {details["reason"]}'
            Logger.log(
                f'💯 Remain {stringify(_view)} syntax "{get_syntax_name(syntax)}" because {stringify(details)}',
                window=_window,
            )
            continue

        _view.assign_syntax(syntax)
        Logger.log(
            f"✔ Change {stringify(_view)} syntax"
            + f' from "{get_syntax_name(syntax_old)}" to "{get_syntax_name(syntax)}" because {stringify(details)}',
            window=_window,
        )

    return True
