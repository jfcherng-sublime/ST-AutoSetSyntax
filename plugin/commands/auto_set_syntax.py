from ..constant import PLUGIN_NAME
from ..constant import RE_VIM_SYNTAX_LINE
from ..constant import VIEW_RUN_ID_SETTINGS_KEY
from ..guesslang.client import TransportCallbacks
from ..guesslang.types import GuesslangServerPredictionItem, GuesslangServerResponse
from ..helper import find_syntax_by_syntax_like
from ..helper import first
from ..helper import generate_trimmed_strings
from ..helper import get_view_by_id
from ..helper import head_tail_content
from ..helper import is_plaintext_syntax
from ..helper import is_syntaxable_view
from ..helper import stringify
from ..libs import websocket
from ..logger import Logger
from ..rules import SyntaxRuleCollection
from ..settings import get_merged_plugin_setting
from ..settings import get_merged_plugin_settings
from ..settings import pref_trim_suffixes
from ..shared import G
from ..snapshot import ViewSnapshot
from operator import itemgetter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import sublime
import sublime_plugin
import uuid


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    def run(self, edit: sublime.Edit, event_name: str = "command") -> None:
        run_auto_set_syntax_on_view(self.view, event_name)


class GuesslangClientCallbacks(TransportCallbacks):
    heuristic_starting_map = {
        "{": "json",
        "---\n": "yaml",
        "-- ": "lua",
        "[[": "toml",
        "[": "ini",
        "<?php": "php",
        "<?xml": "xml",
    }

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        Logger.log(sublime.active_window(), "🤝 Connected to the guesslang server!")
        sublime.status_message("Connected to the guesslang server!")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            response: GuesslangServerResponse = sublime.decode_value(message)
            # shorthands
            view_id = response["id"]
            predictions = response["data"]
            event_name = response["event_name"]
        except (TypeError, ValueError):
            Logger.log(sublime.active_window(), f"💬 Guesslang server says: {message}")
            return

        if not predictions or not (view := get_view_by_id(view_id)):
            return

        predictions.sort(key=itemgetter("confidence"), reverse=True)
        syntax, confidence, is_heuristic = self.resolve_guess_predictions(view, predictions)

        if not syntax:
            return

        if is_heuristic:
            details: Dict[str, Any] = {"event": event_name, "reason": "predict (heuristic)"}
            status_message = f'Predicted as "{syntax.name}" by heuristics'
        else:
            details = {"event": event_name, "reason": "predict", "predictions": predictions[:3]}
            status_message = f'Predicted as "{syntax.name}" ({int(confidence * 100)}% confidence)'

        assign_syntax_to_view(view, syntax, details=details)
        sublime.status_message(status_message)

    def on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        pass

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        Logger.log(sublime.active_window(), "💔 Guesslang server disconnected...")
        sublime.status_message("Guesslang server disconnected...")

    @staticmethod
    def resolve_best_syntax_likes(syntax_likes: Sequence[Union[str, sublime.Syntax]]) -> Optional[sublime.Syntax]:
        return first(find_syntax_by_syntax_like(syntax_like, allow_plaintext=False) for syntax_like in syntax_likes)

    @classmethod
    def resolve_guess_predictions(
        cls,
        view: sublime.View,
        predictions: List[GuesslangServerPredictionItem],
    ) -> Tuple[Optional[sublime.Syntax], float, bool]:
        failed_ret = (None, 1.0, False)

        if not predictions or not (window := view.window()):
            return failed_ret

        settings = get_merged_plugin_settings(window)
        syntax_map: Dict[str, List[str]] = settings.get("guesslang.syntax_map", {})
        min_confidence: float = settings.get("guesslang.confidence_threshold", 0)
        allow_heuristic_guess: bool = settings.get("guesslang.allow_heuristic_guess", True)

        best_prediction = predictions[0]
        if best_prediction["confidence"] < min_confidence:
            if allow_heuristic_guess and (syntax := cls.heuristic_guess(view, syntax_map)):
                return (syntax, 0.0, True)
            return failed_ret

        syntax_likes = syntax_map.get(best_prediction["languageId"], None)
        if not syntax_likes:
            Logger.log(window, f'🤔 Unknown "languageId" from guesslang: {best_prediction["languageId"]}')
            return failed_ret

        if not (syntax := cls.resolve_best_syntax_likes(syntax_likes)):
            return failed_ret

        return (syntax, best_prediction["confidence"], False)

    @classmethod
    def heuristic_guess(cls, view: sublime.View, syntax_map: Dict[str, List[str]]) -> Optional[sublime.Syntax]:
        code = view.substr(sublime.Region(0, 80)).lstrip()
        for start, language_id in cls.heuristic_starting_map.items():
            if (
                code.startswith(start)
                and (syntax_likes := syntax_map.get(language_id, None))
                and (syntax := cls.resolve_best_syntax_likes(syntax_likes))
            ):
                return syntax
        return None


def _snapshot_view(func: Callable) -> Callable:
    def wrapped(view: sublime.View, *args: Any, **kwargs: Any) -> Any:
        run_id = str(uuid.uuid4())
        settings = view.settings()

        settings.set(VIEW_RUN_ID_SETTINGS_KEY, run_id)
        ViewSnapshot.add(run_id, view)
        result = func(view, *args, **kwargs)
        ViewSnapshot.remove(run_id)
        settings.erase(VIEW_RUN_ID_SETTINGS_KEY)

        return result

    return wrapped


@_snapshot_view
def run_auto_set_syntax_on_view(
    view: sublime.View,
    event_name: Optional[str] = None,
    must_plaintext: bool = False,
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

    if event_name in ("command", "load", "paste"):
        # this is the ultimate fallback and done async
        _assign_syntax_with_guesslang_async(view, event_name)

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
    # Note that this only works for files under some circumstances.
    # This is to prevent from, for example, changing a ".erb" (Rails HTML template) file into HTML syntax.
    # But we want to change a file whose name is "cpp" with a Python shebang into Python syntax.
    if (
        (view_info := ViewSnapshot.get_by_view(view))
        and (first_line := view_info["first_line"])
        and (syntax_old := view_info["syntax"])
    ):
        syntax: Optional[sublime.Syntax] = None

        if is_plaintext_syntax(syntax_old) or "." not in view_info["file_name"]:
            # for when modifying the first line or having a shebang
            syntax = sublime.find_syntax_for_file("", first_line)
            # VIM modeline
            if (not syntax or is_plaintext_syntax(syntax)) and (match := RE_VIM_SYNTAX_LINE.search(first_line)):
                syntax = find_syntax_by_syntax_like(match.group("syntax"))

        if not syntax or is_plaintext_syntax(syntax):
            return False

        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event_name, "reason": 'syntax "first_line_match"'},
        )
    return False


def _assign_syntax_with_trimmed_filename(view: sublime.View, event_name: Optional[str] = None) -> bool:
    if not (
        (filepath := view.file_name())
        and (window := view.window())
        and (syntax_old := view.syntax())
        and is_plaintext_syntax(syntax_old)
    ):
        return False

    for trimmed in generate_trimmed_strings(
        (original := Path(filepath).name),
        (suffixes := pref_trim_suffixes(window)),
    ):
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


def _assign_syntax_with_guesslang_async(view: sublime.View, event_name: Optional[str] = None) -> None:
    if (
        not G.guesslang
        or not (view_info := ViewSnapshot.get_by_view(view))
        or "." in view_info["file_name"]  # don't apply on those have an extension
        or not ((original_syntax := view.syntax()) and original_syntax.name == "Plain Text")
    ):
        return None

    G.guesslang.request_guess(head_tail_content(view_info["content"], 2000), view.id(), event_name=event_name)


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

    _views = view.buffer().views() if same_buffer else (view,)
    for _view in _views:
        if not (_window := _view.window()):
            continue

        if syntax == (syntax_old := view.syntax() or sublime.Syntax("", "", False, "")):
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
