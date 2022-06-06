from ..constant import PLUGIN_NAME
from ..constant import RE_ST_SYNTAX_TEST_LINE
from ..constant import RE_VIM_SYNTAX_LINE
from ..constant import VIEW_RUN_ID_SETTINGS_KEY
from ..guesslang.types import GuesslangServerPredictionItem, GuesslangServerResponse
from ..helper import find_syntax_by_syntax_like
from ..helper import find_syntax_by_syntax_likes
from ..helper import generate_trimmed_filenames
from ..helper import generate_trimmed_strings
from ..helper import get_view_by_id
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
from ..types import ListenerEvent, TD_ViewSnapshot
from itertools import chain
from operator import itemgetter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, cast
import sublime
import sublime_plugin
import uuid

AnyCallable = TypeVar("AnyCallable", bound=Callable[..., Any])


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Auto Set Syntax"

    def run(self, edit: sublime.Edit) -> None:
        run_auto_set_syntax_on_view(self.view, ListenerEvent.COMMAND, must_plaintext=False)


class GuesslangClientCallbacks:
    """This class contains event callbacks for the guesslang server."""

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        self._status_msg_and_log("🤝 Connected to the guesslang server!")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            response: GuesslangServerResponse = sublime.decode_value(message)
            # shorthands
            predictions = response["data"]
            event = ListenerEvent.from_value(response["event_name"])
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
        predictions: List[GuesslangServerPredictionItem],
    ) -> Optional[Tuple[sublime.Syntax, float]]:
        if not predictions:
            return None

        settings = get_merged_plugin_settings(window=window)
        syntax_map: Dict[str, List[str]] = settings.get("guesslang.syntax_map", {})
        min_confidence: float = settings.get("guesslang.confidence_threshold", 0)

        best_prediction = predictions[0]
        # confidence < 0 means unknown confidence
        if 0 <= best_prediction["confidence"] < min_confidence:
            Logger.log(window, f'👎 Prediction confidence too low: {best_prediction["confidence"]}')
            return None

        syntax_likes = cls.resolve_language_id(syntax_map, best_prediction["languageId"])
        if not syntax_likes:
            Logger.log(window, f'🤔 Unknown "languageId" from guesslang: {best_prediction["languageId"]}')
            return None

        if not (syntax := find_syntax_by_syntax_likes(syntax_likes, allow_plaintext=False)):
            Logger.log(window, f"😢 Failed finding syntax from guesslang: {syntax_likes}")
            return None

        return (syntax, best_prediction["confidence"])

    @classmethod
    def resolve_language_id(
        cls,
        syntax_map: Dict[str, List[str]],
        language_id: str,
        *,
        referred: Optional[Set[str]] = None,
    ) -> List[str]:
        res: List[str] = []
        referred = referred or set()
        for syntax_like in syntax_map.get(language_id, []):
            if syntax_like.startswith("="):
                if (language_id := syntax_like.lstrip("=")) not in referred:
                    referred.add(language_id)
                    res.extend(cls.resolve_language_id(syntax_map, language_id, referred=referred))
            else:
                res.append(syntax_like)
        return res

    @staticmethod
    def _status_msg_and_log(msg: str, window: Optional[sublime.Window] = None) -> None:
        Logger.log(window or sublime.active_window(), msg)
        sublime.status_message(msg)


def _snapshot_view(failed_ret: Optional[Any] = None) -> Callable[[AnyCallable], AnyCallable]:
    def decorator(func: AnyCallable) -> AnyCallable:
        def wrapped(view: sublime.View, *args: Any, **kwargs: Any) -> Any:
            if not (view.is_valid() and (window := view.window()) and G.is_plugin_ready(window)):
                print(f"[{PLUGIN_NAME}] ⏳ Calm down! View has gone or the plugin is not ready yet.")
                return failed_ret

            run_id = str(uuid.uuid4())
            settings = view.settings()

            settings.set(VIEW_RUN_ID_SETTINGS_KEY, run_id)
            ViewSnapshot.add(run_id, view)
            result = func(view, *args, **kwargs)
            ViewSnapshot.remove(run_id)
            settings.erase(VIEW_RUN_ID_SETTINGS_KEY)

            return result

        return cast(AnyCallable, wrapped)

    return decorator


@_snapshot_view(failed_ret=False)
def run_auto_set_syntax_on_view(
    view: sublime.View,
    event: Optional[ListenerEvent] = None,
    *,
    must_plaintext: bool = False,
) -> bool:
    if event == ListenerEvent.EXEC:
        return _assign_syntax_for_exec_output(view, event)

    # prerequsites
    if not (
        (window := view.window())
        and is_syntaxable_view(view, must_plaintext)
        and (syntax_rule_collection := G.get_syntax_rule_collection(window)) is not None
    ):
        return False

    if event == ListenerEvent.NEW:
        return _assign_syntax_for_new_view(view, event)

    if _assign_syntax_for_st_syntax_test(view, event):
        return True

    if _assign_syntax_with_plugin_rules(view, syntax_rule_collection, event):
        return True

    if _assign_syntax_with_first_line(view, event):
        return True

    if event in (ListenerEvent.COMMAND, ListenerEvent.LOAD) and _assign_syntax_with_trimmed_filename(view, event):
        return True

    if event in (ListenerEvent.COMMAND, ListenerEvent.LOAD, ListenerEvent.MODIFY, ListenerEvent.PASTE):
        # this is the ultimate fallback and done async
        _assign_syntax_with_guesslang_async(view, event)

    return _sorry_cannot_help(view, event)


def _assign_syntax_for_exec_output(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
    if (
        (window := view.window())
        and (not (syntax_old := view.syntax()) or syntax_old.scope == "text.plain")
        and (exec_file_syntax := get_merged_plugin_setting("exec_file_syntax", window=window))
        and (syntax := find_syntax_by_syntax_like(exec_file_syntax, allow_hidden=True))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "exec output", "exec_file_syntax": exec_file_syntax},
        )
    return False


def _assign_syntax_for_new_view(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
    if (
        (window := view.window())
        and (new_file_syntax := get_merged_plugin_setting("new_file_syntax", window=window))
        and (syntax := find_syntax_by_syntax_like(new_file_syntax, allow_plaintext=False))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "new file", "new_file_syntax": new_file_syntax},
        )
    return False


def _assign_syntax_for_st_syntax_test(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
    if not (
        (view_info := ViewSnapshot.get_by_view(view))
        and (not view_info["syntax"] or is_plaintext_syntax(view_info["syntax"]))
        and (m := RE_ST_SYNTAX_TEST_LINE.search(view_info["first_line"]))
        and (new_syntax := m.group("syntax")).endswith(".sublime-syntax")
        and (syntax := find_syntax_by_syntax_like(new_syntax, allow_hidden=True, allow_plaintext=True))
    ):
        return False

    return assign_syntax_to_view(
        view,
        syntax,
        details={"event": event, "reason": "Sublime Test syntax test file"},
    )


def _assign_syntax_with_plugin_rules(
    view: sublime.View,
    syntax_rule_collection: SyntaxRuleCollection,
    event: Optional[ListenerEvent] = None,
) -> bool:
    if syntax_rule := syntax_rule_collection.test(view, event):
        assert syntax_rule.syntax  # otherwise it should be dropped during optimizing
        return assign_syntax_to_view(
            view,
            syntax_rule.syntax,
            details={"event": event, "reason": "plugin rule", "rule": syntax_rule},
        )
    return False


def _assign_syntax_with_first_line(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
    if not (view_info := ViewSnapshot.get_by_view(view)):
        return False

    # Note that this only works for files under some circumstances.
    # This is to prevent from, for example, changing a ".erb" (Rails HTML template) file into HTML syntax.
    # But we want to change a file whose name is "cpp" with a Python shebang into Python syntax.
    def assign_by_shebang(view_info: TD_ViewSnapshot) -> Optional[sublime.Syntax]:
        if (
            (
                (not view_info["syntax"] or is_plaintext_syntax(view_info["syntax"]))
                or "." not in view_info["file_name"]
                or view_info["first_line"].startswith("#!")
            )
            and (syntax := sublime.find_syntax_for_file("", view_info["first_line"]))
            and not is_plaintext_syntax(syntax)
        ):
            return syntax
        return None

    def assign_by_vim_modeline(view_info: TD_ViewSnapshot) -> Optional[sublime.Syntax]:
        if not view_info["syntax"] or is_plaintext_syntax(view_info["syntax"]):
            for match in RE_VIM_SYNTAX_LINE.finditer(view_info["content"]):
                if syntax := find_syntax_by_syntax_like(match.group("syntax")):
                    return syntax
        return None

    syntax: Optional[sublime.Syntax] = None
    for checker in (
        assign_by_shebang,
        assign_by_vim_modeline,
    ):
        if syntax := checker(view_info):
            break

    if not syntax:
        return False

    return assign_syntax_to_view(
        view,
        syntax,
        details={"event": event, "reason": 'syntax "first_line_match"'},
    )


def _assign_syntax_with_trimmed_filename(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
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
        generate_trimmed_strings(original, trim_suffixes, skip_self=True),
        generate_trimmed_filenames(original, skip_self=True) if trim_suffixes_auto else tuple(),
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


def _assign_syntax_with_guesslang_async(view: sublime.View, event: Optional[ListenerEvent] = None) -> None:
    if not (
        G.guesslang
        and (view_info := ViewSnapshot.get_by_view(view))
        # don't apply on those have an extension
        and (event == ListenerEvent.COMMAND or "." not in view_info["file_name"])
        # only apply on plain text syntax
        and ((syntax := view_info["syntax"]) and syntax.name == "Plain Text")
        # we don't want to use AI model during typing when there is only one line
        # that may result in unwanted behavior such as a new buffer may be assigned to Python
        # right after "import" is typed but it could be JavaScript or TypeScript as well
        and (event != ListenerEvent.MODIFY or "\n" in view_info["content"])
    ):
        return None

    G.guesslang.request_guess_snapshot(view_info, model="vscode-regexp-languagedetection", event=event)


def _sorry_cannot_help(view: sublime.View, event: Optional[ListenerEvent] = None) -> bool:
    details = {"event": event, "reason": "no matching rule"}
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
