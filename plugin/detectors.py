import re
from dataclasses import dataclass
from dataclasses import field
from itertools import chain
from pathlib import Path
from typing import Any
from typing import Final

import sublime

from .constants import PLAIN_TEXT_SCOPE
from .logger import Logger
from .magika import get_magika_ignored_labels
from .magika import get_magika_object
from .magika import resolve_magika_label_with_syntax_map
from .rules import SyntaxRuleCollection
from .settings import MergedSettingsDict
from .snapshot import ViewSnapshot
from .types import ListenerEvent
from .utils import ensure_trailing_newline
from .utils import extract_prefixed_dict
from .utils import find_syntax
from .utils import head_tail_lines
from .utils import is_plaintext_syntax
from .utils import list_trimmed_filenames
from .utils import list_trimmed_strings

_RE_ST_SYNTAX_TEST_LINE = re.compile(r'\bSYNTAX\s+TEST\s+"(?P<syntax>[^"]+)"', re.IGNORECASE)
# captures the raw "-*- ... -*-" payload; _RE_EMACS_MODE_KV then picks the mode name out of it,
# since that payload may be a bare mode name or a "key: value; ..." list containing "mode: ..."
_RE_EMACS_SYNTAX_LINE = re.compile(r"^\s*\#.*?-\*-(?P<syntax>.*?)-\*-", re.IGNORECASE | re.MULTILINE)
_RE_EMACS_MODE_KV = re.compile(r"\bmode\s*:\s*(?P<syntax>[^\s;]+)", re.IGNORECASE)
# the trailing lookahead also accepts end-of-string ("$"), not just whitespace -- a modeline on
# the file's last line with no trailing newline (a common "no newline at end of file" case) has
# nothing after it to satisfy a whitespace-only lookahead
_RE_VIM_SYNTAX_LINE = re.compile(r"\b(?:filetype|ft|syntax)=(?P<syntax>[^\s:]+):?(?=\s|$)", re.IGNORECASE)

_FILE_EVENTS: Final[frozenset[ListenerEvent]] = frozenset({
    ListenerEvent.COMMAND,
    ListenerEvent.INIT,
    ListenerEvent.LOAD,
    ListenerEvent.SAVE,
    ListenerEvent.UNTRANSIENTIZE,
})
"""Events where file-on-disk strategies (trimmed filename, etc.) can run."""

_FILE_OR_EDIT_EVENTS: Final[frozenset[ListenerEvent]] = _FILE_EVENTS | frozenset({
    ListenerEvent.MODIFY,
    ListenerEvent.PASTE,
})
"""Events where file-on-disk and modify-sensitive strategies can run."""


@dataclass(slots=True, frozen=True)
class SyntaxDecision:
    """A detector's verdict that `syntax` should be assigned, and why it was reached."""

    syntax: sublime.Syntax
    """The syntax to assign."""
    reason: str
    """Why this detector decided, in the log's words."""
    details: dict[str, Any] = field(default_factory=dict)
    """Further evidence. Logged after the reason, together with the event that triggered detection."""
    status_message: str | None = None
    """An optional status bar message, shown when this decision is applied."""


def detect(
    view_snapshot: ViewSnapshot,
    syntax_rule_collection: SyntaxRuleCollection,
    event: ListenerEvent,
) -> SyntaxDecision | None:
    """Try each detector in order and return the first decision reached, if any."""
    if decision := _detect_for_st_syntax_test(view_snapshot):
        return decision

    if decision := _detect_with_plugin_rules(view_snapshot, syntax_rule_collection, event):
        return decision

    if decision := _detect_with_first_line(view_snapshot, event):
        return decision

    if event in _FILE_EVENTS and (decision := _detect_with_trimmed_filename(view_snapshot)):
        return decision

    if event in _FILE_OR_EDIT_EVENTS and (decision := _detect_with_magika(view_snapshot, event)):
        return decision

    return _detect_with_heuristics(view_snapshot)


def detect_for_exec_output(
    view: sublime.View,
    settings: MergedSettingsDict,
) -> SyntaxDecision | None:
    if (
        view.is_valid()
        and (not (syntax_old := view.syntax()) or syntax_old.scope == PLAIN_TEXT_SCOPE)
        and (exec_file_syntax := settings.get("exec_file_syntax"))
        and (syntax := find_syntax(exec_file_syntax, include_hidden=True))
    ):
        return SyntaxDecision(syntax, "exec output", {"exec_file_syntax": exec_file_syntax})
    return None


def detect_for_new_view(view_snapshot: ViewSnapshot) -> SyntaxDecision | None:
    if (
        view_snapshot.valid_view
        and (new_file_syntax := view_snapshot.settings.get("new_file_syntax"))
        and (syntax := find_syntax(new_file_syntax, include_plaintext=False))
    ):
        return SyntaxDecision(syntax, "new file", {"new_file_syntax": new_file_syntax})
    return None


def _detect_for_st_syntax_test(view_snapshot: ViewSnapshot) -> SyntaxDecision | None:
    if (
        (view := view_snapshot.valid_view)
        and view_snapshot.file_name.startswith("syntax_test_")
        and (m := _RE_ST_SYNTAX_TEST_LINE.search(view_snapshot.first_line))
    ):
        new_syntax: str = m.group("syntax")
        if syntax := find_syntax(new_syntax, include_hidden=True, include_plaintext=True):
            return SyntaxDecision(syntax, "Sublime Test syntax test file")
        Logger.log(f"😢 Cannot find the syntax under test: {new_syntax}", window=view.window())

    return None


def _detect_with_plugin_rules(
    view_snapshot: ViewSnapshot,
    syntax_rule_collection: SyntaxRuleCollection,
    event: ListenerEvent,
) -> SyntaxDecision | None:
    if view_snapshot.valid_view and (syntax_rule := syntax_rule_collection.test(view_snapshot, event)):
        assert syntax_rule.syntax  # otherwise it should be dropped during optimizing
        return SyntaxDecision(syntax_rule.syntax, "plugin rule", {"rule": syntax_rule})
    return None


def _detect_with_first_line(view_snapshot: ViewSnapshot, event: ListenerEvent) -> SyntaxDecision | None:
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
        modeline_lines: int = view_snapshot.settings["modeline_lines"]
        modeline_content = head_tail_lines(view_snapshot.content, modeline_lines)

        # Emacs's "-*- ... -*-" payload is either a bare mode name ("-*- python -*-") or a
        # "key: value; ..." list that may or may not contain a "mode" key ("-*- coding: utf-8;
        # mode: python -*-", in any order) -- the mode name has to be picked out of that payload
        # rather than used as-is.
        for emacs_match in _RE_EMACS_SYNTAX_LINE.finditer(modeline_content):
            payload = emacs_match.group("syntax")
            if mode_match := _RE_EMACS_MODE_KV.search(payload):
                mode_name = mode_match.group("syntax")
            elif ":" not in payload:
                mode_name = payload.strip()
            else:
                continue  # a "key: value" list with no "mode" key -- nothing usable here
            if mode_name and (syntax := find_syntax(mode_name)):
                return syntax

        for vim_match in _RE_VIM_SYNTAX_LINE.finditer(modeline_content):
            if syntax := find_syntax(vim_match.group("syntax")):
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

    if not view_snapshot.valid_view:
        return None

    # It's potentially that a first line of a syntax is a prefix of another syntax's.
    # Thus if the user is typing, only try assigning syntax if this is not triggered by the first line.
    if event is ListenerEvent.MODIFY and view_snapshot.caret_rowcol[0] == 0:
        return None

    for checker in (_prefer_shebang, _prefer_modeline, _prefer_general_first_line):
        if syntax := checker(view_snapshot):
            return SyntaxDecision(
                syntax,
                f'syntax "first_line_match" or "file_extensions" by {checker.__name__}',
            )

    return None


def _detect_with_trimmed_filename(view_snapshot: ViewSnapshot) -> SyntaxDecision | None:
    if not (
        (view := view_snapshot.valid_view)
        and (filepath := view.file_name())
        and (syntax_old := view_snapshot.syntax)
        and is_plaintext_syntax(syntax_old)
    ):
        return None

    original = Path(filepath).name
    trim_suffixes = view_snapshot.trim_suffixes
    trim_suffixes_auto = view_snapshot.settings["trim_suffixes_auto"]

    filenames = chain(
        list_trimmed_strings(original, trim_suffixes, skip_self=True),
        list_trimmed_filenames(original, skip_self=True) if trim_suffixes_auto else (),
    )

    for filename in filenames:
        if (syntax := sublime.find_syntax_for_file(filename)) and not is_plaintext_syntax(syntax):
            return SyntaxDecision(
                syntax,
                "trimmed filename",
                {
                    "filename_original": original,
                    "filename_trimmed": filename,
                    "trim_suffixes": trim_suffixes,
                    "trim_suffixes_auto": trim_suffixes_auto,
                },
            )
    return None


def _detect_with_magika(view_snapshot: ViewSnapshot, event: ListenerEvent) -> SyntaxDecision | None:
    settings = view_snapshot.settings
    if not (
        settings.get("magika.enabled")
        and (magika_obj := get_magika_object())
        and (view := view_snapshot.valid_view)
        and (window := view.window())
        and (event == ListenerEvent.COMMAND or "." not in view_snapshot.file_name_unhidden)
        and ((syntax := view_snapshot.syntax) and is_plaintext_syntax(syntax))
        # we don't want to use AI model during typing when there is only one line
        # that may result in unwanted behavior such as a new buffer may be assigned to Python
        # right after "import" is typed but it could be JavaScript or TypeScript as well
        and (event != ListenerEvent.MODIFY or "\n" in view_snapshot.content)
    ):
        return None

    if view_snapshot.path_obj and not view.is_dirty():
        magika_result = magika_obj.identify_path(view_snapshot.path_obj)
    else:
        magika_result = magika_obj.identify_bytes(ensure_trailing_newline(view_snapshot.content_bytes))
    if not magika_result.ok:
        Logger.log(f"😢 Magika failed: {magika_result.status}", window=window)
        return None
    Logger.log(f"🐛 Magika's prediction: {magika_result!r}", window=window)

    # note that "magika_result.output" may be overridden due to low confidence,
    # while "magika_result.dl" is the raw result
    magika_label = magika_result.dl.label
    magika_score = magika_result.score  # range: 0.0 ~ 1.0

    threshold: float = settings["magika.min_confidence"]
    if magika_score < threshold or magika_label in get_magika_ignored_labels():
        return None

    syntax_map: dict[str, list[str]] = extract_prefixed_dict(settings, prefix="magika.syntax_map.")
    if not (syntax_likes := resolve_magika_label_with_syntax_map(magika_label, syntax_map)):
        Logger.log(f"😢 Magika syntax map resolution failed for label: {magika_label}", window=window)
        return None

    if not (syntax := find_syntax(syntax_likes, include_plaintext=False)):
        Logger.log(f"😢 Failed mapping the label from Magika: {syntax_likes}", window=window)
        return None

    confidence = round(magika_score * 100, 2)
    return SyntaxDecision(
        syntax,
        "Magika (Deep Learning)",
        status_message=f"Predicted label: {magika_label} ({confidence}% confidence)",
    )


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


def _detect_with_heuristics(view_snapshot: ViewSnapshot) -> SyntaxDecision | None:
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
            (_RE_JSON_MAP_BEGIN.search(text_begin) and _RE_JSON_MAP_END.search(text_end))
            or (_RE_JSON_ARRAY_BEGIN.search(text_begin) and _RE_JSON_ARRAY_END.search(text_end))
            or (_RE_JSON_NESTED_ARRAY_BEGIN.search(text_begin) and _RE_JSON_NESTED_ARRAY_END.search(text_end))
            or (_RE_JSON_NESTED_OBJECT_BEGIN.search(text_begin) and _RE_JSON_NESTED_OBJECT_END.search(text_end))
        )

    if not (view_snapshot.valid_view and view_snapshot.syntax and is_plaintext_syntax(view_snapshot.syntax)):
        return None

    if is_json(view_snapshot) and (syntax := find_syntax("scope:source.json")):
        return SyntaxDecision(syntax, "heuristics")

    return None
