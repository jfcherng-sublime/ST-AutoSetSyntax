from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from functools import wraps
from itertools import chain
from operator import itemgetter
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Mapping, TypeVar, cast

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, RE_ST_SYNTAX_TEST_LINE, RE_VIM_SYNTAX_LINE, VIEW_RUN_ID_SETTINGS_KEY
from ..guesslang.types import GuesslangServerPredictionItem, GuesslangServerResponse
from ..helpers import is_syntaxable_view
from ..libs import websocket
from ..logger import Logger
from ..rules import SyntaxRuleCollection
from ..settings import get_merged_plugin_setting, get_merged_plugin_settings, pref_trim_suffixes
from ..shared import G
from ..snapshot import ViewSnapshot, ViewSnapshotCollection
from ..types import ListenerEvent
from ..utils import (
    find_syntax_by_syntax_like,
    find_syntax_by_syntax_likes,
    first_true,
    get_view_by_id,
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


class GuesslangClientCallbacks:
    """This class contains event callbacks for the guesslang server."""

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        self._status_msg_and_log(f"🤝 Connected to guesslang server: {ws.url}")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            response: GuesslangServerResponse = sublime.decode_value(message)
            # shorthands
            predictions = response["data"]
            event = ListenerEvent.from_value(response["event_name"])
            view_id = response["id"]
            Logger.log(f"🐛 Guesslang top predictions: {predictions[:5]}")
        except (TypeError, ValueError):
            Logger.log(f"💬 Guesslang server says: {message}")
            return
        except Exception as e:
            Logger.log(f"💣 Guesslang exception: {e}")
            return

        if not predictions or not (view := get_view_by_id(view_id)) or not (window := view.window()):
            return

        predictions.sort(key=itemgetter("confidence"), reverse=True)

        if not (resolved_prediction := self.resolve_guess_predictions(window, predictions)):
            return

        # on_message() callback is async and maybe now the syntax has been set by other things somehow
        if (current_syntax := view.syntax()) and not is_plaintext_syntax(current_syntax):
            return

        best_syntax, confidence = resolved_prediction
        details = {"event": event, "reason": "predict", "confidence": confidence}
        status_message = f'Predicted as "{best_syntax.name}"'
        if confidence >= 0:
            status_message += f" ({int(confidence * 100)}% confidence)"

        assign_syntax_to_view(view, best_syntax, details=details)
        sublime.status_message(status_message)

    def on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        self._status_msg_and_log(f"❌ Guesslang server went wrong: {error}")

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        self._status_msg_and_log("💔 Guesslang server disconnected...")

    @classmethod
    def resolve_guess_predictions(
        cls,
        window: sublime.Window,
        predictions: Iterable[GuesslangServerPredictionItem],
    ) -> tuple[sublime.Syntax, float] | None:
        if not (best_prediction := first_true(predictions)):
            return None

        settings = get_merged_plugin_settings(window=window)
        syntax_map: dict[str, list[str]] = settings.get("guesslang.syntax_map", {})

        if not (syntax_likes := cls.resolve_language_id(syntax_map, best_prediction["languageId"])):
            Logger.log(f'🤔 Unknown "languageId" from guesslang: {best_prediction["languageId"]}', window=window)
            return None

        if not (syntax := find_syntax_by_syntax_likes(syntax_likes, include_plaintext=False)):
            Logger.log(f"😢 Failed finding syntax from guesslang: {syntax_likes}", window=window)
            return None

        return (syntax, best_prediction["confidence"])

    @classmethod
    def resolve_language_id(
        cls,
        syntax_map: Mapping[str, Iterable[str]],
        language_id: str,
        *,
        referred: set[str] | None = None,
    ) -> list[str]:
        res: list[str] = []
        referred = referred or set()
        for syntax_like in syntax_map.get(language_id, []):
            if syntax_like.startswith("="):
                if (language_id := syntax_like[1:]) not in referred:
                    referred.add(language_id)
                    res.extend(cls.resolve_language_id(syntax_map, language_id, referred=referred))
            else:
                res.append(syntax_like)
        return res

    @staticmethod
    def _status_msg_and_log(msg: str, window: sublime.Window | None = None) -> None:
        Logger.log(msg, window=window)
        sublime.status_message(msg)


@contextmanager
def _view_snapshot_context(view: sublime.View) -> Generator[ViewSnapshot, None, None]:
    run_id = str(uuid.uuid4())
    settings = view.settings()

    try:
        settings.set(VIEW_RUN_ID_SETTINGS_KEY, run_id)
        ViewSnapshotCollection.add(run_id, view)
        yield ViewSnapshotCollection.get(run_id)  # type: ignore
    finally:
        settings.erase(VIEW_RUN_ID_SETTINGS_KEY)
        ViewSnapshotCollection.pop(run_id)


def _snapshot_view(failed_ret: Any = None) -> Callable[[_T_Callable], _T_Callable]:
    def decorator(func: _T_Callable) -> _T_Callable:
        @wraps(func)
        def wrapped(view: sublime.View, *args: Any, **kwargs: Any) -> Any:
            if not ((window := view.window()) and G.is_plugin_ready(window) and view.is_valid()):
                Logger.log("⏳ Calm down! View has gone or the plugin is not ready yet.")
                return failed_ret

            with _view_snapshot_context(view):
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
        and is_syntaxable_view(view, must_plaintext)
        and (syntax_rule_collection := G.get_syntax_rule_collection(window))
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

    if _assign_syntax_with_special_cases(view, event):
        return True

    if event in {
        ListenerEvent.COMMAND,
        ListenerEvent.INIT,
        ListenerEvent.LOAD,
        ListenerEvent.MODIFY,
        ListenerEvent.PASTE,
        ListenerEvent.SAVE,
        ListenerEvent.UNTRANSIENTIZE,
    }:
        # this is the ultimate fallback and done async
        _assign_syntax_with_guesslang_async(view, event)

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
        (view_snapshot := ViewSnapshotCollection.get_by_view(view))
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
    if not (view_snapshot := ViewSnapshotCollection.get_by_view(view)):
        return False

    # Note that this only works for files under some circumstances.
    # This is to prevent from, for example, changing a ".erb" (Rails HTML template) file into HTML syntax.
    # But we want to change a file whose name is "cpp" with a Python shebang into Python syntax.
    def assign_by_shebang(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        if (
            view_snapshot.syntax
            and not is_plaintext_syntax(view_snapshot.syntax)
            and ("." not in view_snapshot.file_name_unhidden or view_snapshot.first_line.startswith("#!"))
            and (syntax := sublime.find_syntax_for_file("", view_snapshot.first_line))
            and not is_plaintext_syntax(syntax)
        ):
            return syntax
        return None

    def assign_by_vim_modeline(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        for match in RE_VIM_SYNTAX_LINE.finditer(view_snapshot.content):
            if syntax := find_syntax_by_syntax_like(match.group("syntax")):
                return syntax
        return None

    for checker in (assign_by_shebang, assign_by_vim_modeline):
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


def _assign_syntax_with_special_cases(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    if not (
        (view_snapshot := ViewSnapshotCollection.get_by_view(view))
        and view_snapshot.syntax
        and is_plaintext_syntax(view_snapshot.syntax)
    ):
        return False

    def is_large_file(view: sublime.View) -> bool:
        return view.size() >= 10 * 1024  # 10KB

    def is_json(view: sublime.View) -> bool:
        view_size = view.size()
        text_begin = re.sub(r"\s+", "", view.substr(sublime.Region(0, 10)))
        text_end = re.sub(r"\s+", "", view.substr(sublime.Region(view_size - 10, view_size)))

        return bool(
            # map
            (re.search(r'^\{"', text_begin) and re.search(r'(?:[\d"\]}]|true|false|null)\}$', text_end))
            # array
            or (re.search(r'^\["', text_begin) and re.search(r'(?:[\d"\]}]|true|false|null)\]$', text_end))
            or (text_begin.startswith("[[") and text_end.endswith("]]"))
            or (text_begin.startswith("[{") and text_end.endswith("}]"))
        )

    if is_large_file(view):
        if is_json(view) and (syntax := find_syntax_by_syntax_like("scope:source.json")):
            return assign_syntax_to_view(view, syntax, details={"event": event, "reason": "special case"})

    return False


def _assign_syntax_with_guesslang_async(view: sublime.View, event: ListenerEvent | None = None) -> None:
    if not (
        G.guesslang_client
        and (view_snapshot := ViewSnapshotCollection.get_by_view(view))
        # don't apply on those have an extension
        and (event == ListenerEvent.COMMAND or "." not in view_snapshot.file_name_unhidden)
        # only apply on plain text syntax
        and ((syntax := view_snapshot.syntax) and is_plaintext_syntax(syntax))
        # we don't want to use AI model during typing when there is only one line
        # that may result in unwanted behavior such as a new buffer may be assigned to Python
        # right after "import" is typed but it could be JavaScript or TypeScript as well
        and (event != ListenerEvent.MODIFY or "\n" in view_snapshot.content)
    ):
        return

    G.guesslang_client.request_guess_snapshot(view_snapshot, event=event)


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
                f'💯 Remain {stringify(_view)} syntax "{syntax.name}" because {stringify(details)}',
                window=_window,
            )
            continue

        _view.assign_syntax(syntax)
        Logger.log(
            f"✔ Change {stringify(_view)} syntax"
            + f' from "{syntax_old.name}" to "{syntax.name}" because {stringify(details)}',
            window=_window,
        )

    return True
