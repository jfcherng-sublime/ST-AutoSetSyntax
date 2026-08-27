import re
from itertools import chain
from pathlib import Path
from typing import Any
from typing import Final
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..constants import RE_EMACS_MODE_KV
from ..constants import RE_EMACS_SYNTAX_LINE
from ..constants import RE_ST_SYNTAX_TEST_LINE
from ..constants import RE_VIM_SYNTAX_LINE
from ..constants import VIEW_KEY_IS_ASSIGNED
from ..helpers import is_syntaxable_view
from ..logger import Logger
from ..magika import get_magika_ignored_labels
from ..magika import get_magika_object
from ..magika import resolve_magika_label_with_syntax_map
from ..rules import SyntaxRuleCollection
from ..settings import MergedSettingsDict
from ..settings import get_merged_plugin_settings
from ..shared import G
from ..snapshot import ViewSnapshot
from ..types import NULL_SYNTAX
from ..types import ListenerEvent
from ..utils import ensure_trailing_newline
from ..utils import extract_prefixed_dict
from ..utils import find_syntax_by_syntax_like
from ..utils import find_syntax_by_syntax_likes
from ..utils import get_syntax_name
from ..utils import head_tail_lines
from ..utils import is_plaintext_syntax
from ..utils import list_trimmed_filenames
from ..utils import list_trimmed_strings
from ..utils import stringify

_FILE_SAVE_EVENTS: Final[frozenset[ListenerEvent]] = frozenset({
    ListenerEvent.COMMAND,
    ListenerEvent.INIT,
    ListenerEvent.LOAD,
    ListenerEvent.SAVE,
    ListenerEvent.UNTRANSIENTIZE,
})
"""Events where file-on-disk strategies (trimmed filename, etc.) can run."""

_FILE_AND_MODIFY_EVENTS: Final[frozenset[ListenerEvent]] = _FILE_SAVE_EVENTS | frozenset({
    ListenerEvent.MODIFY,
    ListenerEvent.PASTE,
})
"""Events where file-on-disk and modify-sensitive strategies can run."""


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
    skip_syntaxable_check: bool = False,
) -> bool:
    if not ((window := view.window()) and G.is_plugin_ready(window) and view.is_valid()):
        Logger.log("⏳ Calm down! View has gone or the plugin is not ready yet.")
        return False

    # Resolve settings once and reuse across all strategy functions.
    # This avoids repeated ChainMap lookups per strategy.
    settings = get_merged_plugin_settings(window=window)

    # Cheap EXEC short-circuit: no snapshot needed
    if event is ListenerEvent.EXEC:
        return _assign_syntax_for_exec_output(view, event, settings)

    # Cheap prerequisites: reject before building expensive snapshot
    if not (
        (skip_syntaxable_check or is_syntaxable_view(view, must_plaintext=must_plaintext))
        and (syntax_rule_collection := G.syntax_rule_collections.get(window))
    ):
        return False

    # Build expensive snapshot only after all cheap guards pass
    view_snapshot = ViewSnapshot.from_view(view)

    if event is ListenerEvent.NEW:
        return _assign_syntax_for_new_view(view_snapshot, event, settings)

    if _assign_syntax_for_st_syntax_test(view_snapshot, event):
        return True

    if _assign_syntax_with_plugin_rules(view_snapshot, syntax_rule_collection, event):
        return True

    if _assign_syntax_with_first_line(view_snapshot, event, settings):
        return True

    if event in _FILE_SAVE_EVENTS and _assign_syntax_with_trimmed_filename(view_snapshot, event, settings):
        return True

    if event in _FILE_AND_MODIFY_EVENTS and _assign_syntax_with_magika(view_snapshot, event, settings):
        return True

    if _assign_syntax_with_heuristics(view_snapshot, event):
        return True

    return _sorry_cannot_help(view, event)


def _assign_syntax_for_exec_output(
    view: sublime.View,
    event: ListenerEvent | None = None,
    settings: MergedSettingsDict | None = None,
) -> bool:
    if (
        view.is_valid()
        and (window := view.window())
        and (not (syntax_old := view.syntax()) or syntax_old.scope == "text.plain")
        and (exec_file_syntax := (settings or get_merged_plugin_settings(window=window)).get("exec_file_syntax"))
        and (syntax := find_syntax_by_syntax_like(exec_file_syntax, include_hidden=True))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "exec output", "exec_file_syntax": exec_file_syntax},
        )
    return False


def _assign_syntax_for_new_view(
    view_snapshot: ViewSnapshot,
    event: ListenerEvent | None = None,
    settings: MergedSettingsDict | None = None,
) -> bool:
    if (
        (view := view_snapshot.valid_view)
        and (window := view.window())
        and (new_file_syntax := (settings or get_merged_plugin_settings(window=window)).get("new_file_syntax"))
        and (syntax := find_syntax_by_syntax_like(new_file_syntax, include_plaintext=False))
    ):
        return assign_syntax_to_view(
            view,
            syntax,
            details={"event": event, "reason": "new file", "new_file_syntax": new_file_syntax},
        )
    return False


def _assign_syntax_for_st_syntax_test(view_snapshot: ViewSnapshot, event: ListenerEvent | None = None) -> bool:
    if (
        (view := view_snapshot.valid_view)
        and view_snapshot.file_name.startswith("syntax_test_")
        and (m := RE_ST_SYNTAX_TEST_LINE.search(view_snapshot.first_line))
    ):
        new_syntax: str = m.group("syntax")
        if syntax := find_syntax_by_syntax_like(new_syntax, include_hidden=True, include_plaintext=True):
            return assign_syntax_to_view(
                view,
                syntax,
                details={"event": event, "reason": "Sublime Test syntax test file"},
            )
        Logger.log(f"😢 Cannot find the syntax under test: {new_syntax}", window=view.window())

    return False


def _assign_syntax_with_plugin_rules(
    view_snapshot: ViewSnapshot,
    syntax_rule_collection: SyntaxRuleCollection,
    event: ListenerEvent | None = None,
) -> bool:
    if (view := view_snapshot.valid_view) and (syntax_rule := syntax_rule_collection.test(view_snapshot, event)):
        assert syntax_rule.syntax  # otherwise it should be dropped during optimizing
        return assign_syntax_to_view(
            view,
            syntax_rule.syntax,
            details={"event": event, "reason": "plugin rule", "rule": syntax_rule},
        )
    return False


def _assign_syntax_with_first_line(
    view_snapshot: ViewSnapshot,
    event: ListenerEvent | None = None,
    settings: MergedSettingsDict | None = None,
) -> bool:
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

    def _prefer_modeline(view_snapshot: ViewSnapshot) -> sublime.Syntax | None:
        # Real Vim/Emacs only look for modelines within the first/last few lines of a file
        # (Vim's "modelines" option defaults to 5). If we search the whole (trimmed) file
        # content instead, a "# vim: ..." or "-*- ... -*-" line that merely appears inside a
        # code block somewhere in the document (e.g., a Markdown fenced code example) would be
        # wrongly treated as a real modeline. See https://github.com/jfcherng-sublime/ST-AutoSetSyntax/issues/30
        # a key explicitly set to `null` is present with value None, not absent, so `.get(..., 5)`'s
        # default alone doesn't cover it -- `int(None)` would raise TypeError. Check for None
        # explicitly rather than falsy (`modeline_lines: 0` is a distinct, valid "no modeline
        # search at all" setting -- see head_tail_lines()'s `n == 0` case -- and must not be
        # coerced into the default.)
        modeline_lines_setting = (settings or get_merged_plugin_settings(window=window)).get("modeline_lines")
        modeline_lines = int(modeline_lines_setting if modeline_lines_setting is not None else 5)
        modeline_content = head_tail_lines(view_snapshot.content, modeline_lines)

        # Emacs's "-*- ... -*-" payload is either a bare mode name ("-*- python -*-") or a
        # "key: value; ..." list that may or may not contain a "mode" key ("-*- coding: utf-8;
        # mode: python -*-", in any order) -- the mode name has to be picked out of that payload
        # rather than used as-is.
        for emacs_match in RE_EMACS_SYNTAX_LINE.finditer(modeline_content):
            payload = emacs_match.group("syntax")
            if mode_match := RE_EMACS_MODE_KV.search(payload):
                mode_name = mode_match.group("syntax")
            elif ":" not in payload:
                mode_name = payload.strip()
            else:
                continue  # a "key: value" list with no "mode" key -- nothing usable here
            if mode_name and (syntax := find_syntax_by_syntax_like(mode_name)):
                return syntax

        for vim_match in RE_VIM_SYNTAX_LINE.finditer(modeline_content):
            if syntax := find_syntax_by_syntax_like(vim_match.group("syntax")):
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

    if not ((view := view_snapshot.valid_view) and (window := view.window())):
        return False

    # It's potentially that a first line of a syntax is a prefix of another syntax's.
    # Thus if the user is typing, only try assigning syntax if this is not triggered by the first line.
    if event is ListenerEvent.MODIFY and view_snapshot.caret_rowcol[0] == 0:
        return False

    for checker in (_prefer_shebang, _prefer_modeline, _prefer_general_first_line):
        if syntax := checker(view_snapshot):
            return assign_syntax_to_view(
                view,
                syntax,
                details={
                    "event": event,
                    "reason": f'syntax "first_line_match" or "file_extensions" by {checker.__name__}',
                },
            )

    return False


def _assign_syntax_with_trimmed_filename(
    view_snapshot: ViewSnapshot,
    event: ListenerEvent | None = None,
    settings: MergedSettingsDict | None = None,
) -> bool:
    if not (
        (view := view_snapshot.valid_view)
        and (filepath := view.file_name())
        and (window := view.window())
        and (syntax_old := view.syntax())
        and is_plaintext_syntax(syntax_old)
    ):
        return False

    settings = settings or get_merged_plugin_settings(window=window)
    original = Path(filepath).name
    trim_suffixes = settings.get("trim_suffixes", ())
    trim_suffixes_auto = settings.get("trim_suffixes_auto", False)

    filenames = chain(
        list_trimmed_strings(original, trim_suffixes, skip_self=True),
        list_trimmed_filenames(original, skip_self=True) if trim_suffixes_auto else (),
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


_MAGIKA_SAMPLE_CHAR_BUDGET: Final[int] = 16 * 1024
"""Max characters of view content handed to Magika as a bytes sample.

Magika only inspects the first/last few KB of content anyway, while `view_snapshot.content`
is unbounded when `trim_file_size` is negative -- encoding the whole buffer per event would
be a freeze/memory risk on the UI thread. Mirrors `head_tail_content_st`'s head+tail shape.
"""


def _magika_sample_bytes(view_snapshot: ViewSnapshot) -> bytes:
    content = view_snapshot.content
    if len(content) <= _MAGIKA_SAMPLE_CHAR_BUDGET:
        return view_snapshot.content_bytes

    half = _MAGIKA_SAMPLE_CHAR_BUDGET // 2
    return (content[:half] + "\n\n" + content[-half:]).encode(view_snapshot.encoding_py)


def _assign_syntax_with_magika(
    view_snapshot: ViewSnapshot,
    event: ListenerEvent | None = None,
    settings: MergedSettingsDict | None = None,
) -> bool:
    if not (
        (magika_obj := get_magika_object())
        and (view := view_snapshot.valid_view)
        and (window := view.window())
        and (settings := settings or get_merged_plugin_settings(window=window))
        and settings.get("magika.enabled")
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
        if view_snapshot.path_obj and not view.is_dirty():
            magika_result = magika_obj.identify_path(view_snapshot.path_obj)
        else:
            magika_result = magika_obj.identify_bytes(ensure_trailing_newline(_magika_sample_bytes(view_snapshot)))
    except Exception as e:
        # `result.ok` below only covers status-coded failures; MagikaError/OSError from a broken
        # dependency install escape the call itself and must not abort syntax detection
        Logger.log(f"😢 Magika raised during identification: {e}", window=window)
        return False
    if not magika_result.ok:
        Logger.log(f"😢 Magika failed: {magika_result.status}", window=window)
        return False
    Logger.log(f"🐛 Magika's prediction: {magika_result!r}", window=window)

    # note that "magika_result.output" may be overridden due to low confidence,
    # while "magika_result.dl" is the raw result
    magika_label = magika_result.dl.label
    magika_score = magika_result.score  # range: 0.0 ~ 1.0

    threadshold: float = settings.get("magika.min_confidence", 0.0)
    if magika_score < threadshold or magika_label in get_magika_ignored_labels():
        return False

    syntax_map: dict[str, list[str]] = extract_prefixed_dict(settings, prefix="magika.syntax_map.")
    if not (syntax_likes := resolve_magika_label_with_syntax_map(magika_label, syntax_map)):
        Logger.log(f"😢 Magika syntax map resolution failed for label: {magika_label}", window=window)
        return False

    if not (syntax := find_syntax_by_syntax_likes(syntax_likes, include_plaintext=False)):
        Logger.log(f"😢 Failed mapping the label from Magika: {syntax_likes}", window=window)
        return False

    confidence = round(magika_score * 100, 2)
    sublime.status_message(f"Predicted label: {magika_label} ({confidence}% confidence)")
    return assign_syntax_to_view(view, syntax, details={"event": event, "reason": "Magika (Deep Learning)"})


# tolerate whitespace right after the opening bracket / right before the closing one, since
# pretty-printed JSON (e.g. `json.dumps(x, indent=2)`) -- arguably the most common shape a user
# would actually paste or open -- always has a newline/indentation there, not a bare `{"`/`}`
_RE_JSON_MAP_BEGIN: Final = re.compile(r'^\{\s*"')
_RE_JSON_MAP_END: Final = re.compile(r'(?:[\d"\]}]|true|false|null)\s*\}$')
_RE_JSON_ARRAY_BEGIN: Final = re.compile(r'^\[\s*"')
_RE_JSON_ARRAY_END: Final = re.compile(r'(?:[\d"\]}]|true|false|null)\s*\]$')
_RE_JSON_NESTED_ARRAY_BEGIN: Final = re.compile(r"^\[\s*\[")
_RE_JSON_NESTED_ARRAY_END: Final = re.compile(r"\]\s*\]$")
_RE_JSON_NESTED_OBJECT_BEGIN: Final = re.compile(r"^\[\s*\{")
_RE_JSON_NESTED_OBJECT_END: Final = re.compile(r"\}\s*\]$")

_SMALL_FILE_SIZE: Final[int] = 1 * 1024  # 1 KB

_XSSI_PREFIXES: Final[tuple[str, ...]] = (")]}'\n", ")]}',\n")


def _assign_syntax_with_heuristics(view_snapshot: ViewSnapshot, event: ListenerEvent | None = None) -> bool:
    def is_small_file(view_snapshot: ViewSnapshot) -> bool:
        return view_snapshot.char_count < _SMALL_FILE_SIZE

    def is_json(view_snapshot: ViewSnapshot) -> bool:
        # strip whitespace from the *whole* (already size-bounded) content before slicing --
        # slicing first would let >= 10 chars of leading/trailing padding (blank lines, etc.)
        # swallow the slice window entirely, hiding real JSON content from the regexes below
        text_begin = view_snapshot.content.lstrip()[:10]
        text_end = view_snapshot.content.rstrip()[-10:]

        # XSSI protection prefix (https://security.stackexchange.com/q/110539)
        if text_begin.startswith(_XSSI_PREFIXES):
            return True

        return not is_small_file(view_snapshot) and bool(
            # map
            (_RE_JSON_MAP_BEGIN.search(text_begin) and _RE_JSON_MAP_END.search(text_end))
            # array
            or (_RE_JSON_ARRAY_BEGIN.search(text_begin) and _RE_JSON_ARRAY_END.search(text_end))
            # array of arrays
            or (_RE_JSON_NESTED_ARRAY_BEGIN.search(text_begin) and _RE_JSON_NESTED_ARRAY_END.search(text_end))
            # array of objects
            or (_RE_JSON_NESTED_OBJECT_BEGIN.search(text_begin) and _RE_JSON_NESTED_OBJECT_END.search(text_end))
        )

    if not ((view := view_snapshot.valid_view) and view_snapshot.syntax and is_plaintext_syntax(view_snapshot.syntax)):
        return False

    if is_json(view_snapshot) and (syntax := find_syntax_by_syntax_like("scope:source.json")):
        return assign_syntax_to_view(view, syntax, details={"event": event, "reason": "heuristics"})

    return False


def _sorry_cannot_help(view: sublime.View, event: ListenerEvent | None = None) -> bool:
    details: dict[str, Any] = {"event": event, "reason": "no matching rule"}
    Logger.log(lambda: f"❌ Cannot help {stringify(view)} because {stringify(details)}", window=view.window())
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

    views = view.buffer().views() if same_buffer else (view,)
    for view_ in views:
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
