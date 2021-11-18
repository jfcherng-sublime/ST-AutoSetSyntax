from ..constant import PLUGIN_NAME
from ..constant import RE_VIM_SYNTAX_LINE
from ..constant import VIEW_RUN_ID_SETTINGS_KEY
from ..guesslang.types import GuesslangServerPredictionItem, GuesslangServerResponse
from ..helper import find_syntax_by_syntax_like
from ..helper import find_syntax_by_syntax_likes
from ..helper import generate_trimmed_strings
from ..helper import get_view_by_id
from ..helper import head_tail_content_st
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
from ..types import TD_ViewSnapshot
from operator import itemgetter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import re
import sublime
import sublime_plugin
import uuid


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    def run(self, edit: sublime.Edit, event_name: str = "command") -> None:
        run_auto_set_syntax_on_view(self.view, event_name)


class GuesslangClientCallbacks:
    """This class contains event callbacks for the guesslang server."""

    heuristic_head_tail_map: Dict[Tuple[str, str], str] = {
        # (head, tail): languageId,
        ("[{", "}]"): "json",
        ("[[", "]]"): "json",
        ("{", "}"): "json",
        ("[", ""): "ini",
        ("---\n", ""): "yaml",
        ("-- phpMyAdmin ", ""): "sql",
        ("-- ", ""): "lua",
        ("<?=", ""): "php",
        ("<?php", ""): "php",
        ("<?xml", ""): "xml",
    }

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        Logger.log(sublime.active_window(), "🤝 Connected to the guesslang server!")
        sublime.status_message("Connected to the guesslang server!")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            response: GuesslangServerResponse = sublime.decode_value(message)
            # shorthands
            predictions = response["data"]
            event_name = response["event_name"]
            view_id = response["id"]
            Logger.log(sublime.active_window(), f"🐛 Guesslang top predictions: {predictions[:5]}")
        except (TypeError, ValueError):
            Logger.log(sublime.active_window(), f"💬 Guesslang server says: {message}")
            return
        except KeyError as e:
            print(f"[{PLUGIN_NAME}] {e}")
            return

        if not predictions or not (view := get_view_by_id(view_id)) or not (window := view.window()):
            return

        content = head_tail_content_st(view, 2000).strip()
        predictions.sort(key=itemgetter("confidence"), reverse=True)
        best_syntax, confidence, is_heuristic = self.resolve_guess_predictions(window, content, predictions)

        if not best_syntax or not self.assert_prediction(content, best_syntax):
            return

        if is_heuristic:
            details: Dict[str, Any] = {"event": event_name, "reason": "predict (heuristic)"}
            status_message = f'Predicted as "{best_syntax.name}" by heuristics'
        else:
            details = {"event": event_name, "reason": "predict", "confidence": confidence}
            status_message = f'Predicted as "{best_syntax.name}" ({int(confidence * 100)}% confidence)'

        # on_message() callback is async and maybe now the syntax has been set by other things somehow
        if (current_syntax := view.syntax()) and not is_plaintext_syntax(current_syntax):
            return

        assign_syntax_to_view(view, best_syntax, details=details)
        sublime.status_message(status_message)

    def on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        pass

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        Logger.log(sublime.active_window(), "💔 Guesslang server disconnected...")
        sublime.status_message("Guesslang server disconnected...")

    @classmethod
    def resolve_guess_predictions(
        cls,
        window: sublime.Window,
        content: str,
        predictions: List[GuesslangServerPredictionItem],
    ) -> Tuple[Optional[sublime.Syntax], float, bool]:
        failed_ret = (None, 1.0, False)

        if not predictions:
            return failed_ret

        settings = get_merged_plugin_settings(window)
        syntax_map: Dict[str, List[str]] = settings.get("guesslang.syntax_map", {})
        min_confidence: float = settings.get("guesslang.confidence_threshold", 0)
        allow_heuristic_guess: bool = settings.get("guesslang.allow_heuristic_guess", True)

        best_prediction = predictions[0]
        if best_prediction["confidence"] < min_confidence:
            if allow_heuristic_guess and (syntax := cls.heuristic_guess(content, syntax_map)):
                return (syntax, 0.0, True)
            return failed_ret

        syntax_likes = syntax_map.get(best_prediction["languageId"], None)
        if not syntax_likes:
            Logger.log(window, f'🤔 Unknown "languageId" from guesslang: {best_prediction["languageId"]}')
            return failed_ret

        if not (syntax := find_syntax_by_syntax_likes(syntax_likes, allow_plaintext=False)):
            return failed_ret

        return (syntax, best_prediction["confidence"], False)

    @classmethod
    def heuristic_guess(cls, content: str, syntax_map: Dict[str, List[str]]) -> Optional[sublime.Syntax]:
        target_language_id = None
        for (head, tail), language_id in cls.heuristic_head_tail_map.items():
            if content.startswith(head) and content.endswith(tail):
                target_language_id = language_id
                break

        if (
            target_language_id
            and (syntax_likes := syntax_map.get(target_language_id, None))
            and (syntax := find_syntax_by_syntax_likes(syntax_likes, allow_plaintext=False))
        ):
            return syntax
        return None

    @staticmethod
    def assert_prediction(content: str, prediction: sublime.Syntax) -> bool:
        """
        Sometimes the model gives prediction which is obviously wrong.
        This function does some simple characteristics check to prevent that.
        """
        # the model seems to predict plain text as "INI" syntax quite frequently...
        if prediction.scope == "source.ini" and not re.search(r"^[^\s=]+\s*=(?=\b|\s|$)", content, re.MULTILINE):
            return False

        return True


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

    if event_name in ("command", "load") and _assign_syntax_with_trimmed_filename(view, event_name):
        return True

    if event_name in ("command", "load", "paste") and (view_info := ViewSnapshot.get_by_view(view)):
        # this is the ultimate fallback and done async
        _assign_syntax_with_guesslang_async(view_info, event_name)

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

        if (
            is_plaintext_syntax(syntax_old)
            or "." not in view_info["file_name"]
            or view_info["first_line"].startswith("#!")
        ):
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


def _assign_syntax_with_guesslang_async(view_info: TD_ViewSnapshot, event_name: Optional[str] = None) -> None:
    if (
        not G.guesslang
        or "." in view_info["file_name"]  # don't apply on those have an extension
        or not ((syntax := view_info["syntax"]) and syntax.name == "Plain Text")
    ):
        return None

    G.guesslang.request_guess_snapshot(view_info, event_name=event_name)


def _sorry_cannot_help(view: sublime.View, event_name: Optional[str] = None) -> bool:
    details = {"event": event_name, "reason": "no matching rule"}
    Logger.log(view.window(), f"❌ Cannot help {stringify(view)} because {stringify(details)}")
    return False


def assign_syntax_to_view(
    view: sublime.View,
    syntax: sublime.Syntax,
    *,
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
