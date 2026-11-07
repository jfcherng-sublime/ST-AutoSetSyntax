import inspect
import operator
import re
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from functools import reduce
from itertools import chain
from pathlib import Path
from re import Pattern
from typing import Any

import sublime
from more_itertools import always_iterable
from more_itertools import first_true
from more_itertools import unique_everseen

from ._vendor.trie import TrieNode
from .cache import clearable_lru_cache
from .types import SyntaxLike
from .types import SyntaxLikes


def camel_to_snake(s: str) -> str:
    """Converts "CamelCase" to "snake_case"."""
    return "".join(f"_{c}" if c.isupper() else c for c in s).strip("_").lower()


def ensure_trailing_newline[T: (str, bytes)](content: T) -> T:
    """Ensures that the content ends with a newline."""
    match content:
        case str():
            return content if content.endswith("\n") else content + "\n"
        case bytes():
            return content if content.endswith(b"\n") else content + b"\n"


@clearable_lru_cache()
def compile_regex(regex: str | re.Pattern[str], flags: int = 0) -> re.Pattern[str]:
    """Compile the regex string/object into a object with the given flags."""
    if isinstance(regex, Pattern):
        if regex.flags == flags:
            return regex
        regex = regex.pattern
    return re.compile(regex, flags)


def drop_falsy[T](iterable: Iterable[T | None]) -> Generator[T]:
    """Drops falsy values from the iterable."""
    yield from filter(None, iterable)


def quote_join(items: Iterable[str]) -> str:
    """Render strings for a message a user reads: `"a", "b"` rather than a container's repr."""
    return ", ".join(f'"{item}"' for item in items)


def get_fqcn(obj: Any) -> str:
    match obj:
        case None:
            return "None"
        case type():
            cls = obj
        case _:
            cls = type(obj)
    return f"{cls.__module__}.{cls.__qualname__}"


def merge_literals_to_regex(literals: Iterable[str]) -> str:
    """
    Merge (non-regex) literal strings into an optimized regex string.

    The returned regex is enclosed as `(?:...)`.
    """
    return merge_regexes(map(re.escape, literals))


def merge_regexes(regexes: Iterable[str]) -> str:
    """Merge regex strings into a single regex string."""
    regexes = tuple(regexes)
    if not regexes:
        return r"~^(?#match nothing)"
    if len(regexes) == 1:
        return f"(?:{regexes[0]})"
    return f"(?:{'|'.join(f'(?:{regex})' for regex in regexes)})"


def parse_regex_flags(flags: Iterable[str]) -> int:
    """
    Parse string regex flags into an int value.

    Valid flags are:
    `A`, `ASCII`, `DEBUG`, `I`, `IGNORECASE`, `L`, `LOCALE`, `M`, `MULTILINE`,
    `S`, `DOTALL`, `X`, `VERBOSE`, `U`, `UNICODE`.

    @see https://docs.python.org/3.13/library/re.html#re.A
    """
    if isinstance(flags, str):
        flags = (flags,)
    return reduce(operator.ior, (getattr(re, flag, 0) for flag in flags), 0)


@clearable_lru_cache()
def build_reversed_trie(words: tuple[str, ...]) -> TrieNode:
    """Returns a trie with all words reversed. It can be used to match suffixes with reversed input string."""
    trie = TrieNode()
    for word in words:
        trie.insert(word[::-1])
    return trie


def list_all_subclasses[T](
    root: type[T],
    skip_abstract: bool = False,
    skip_self: bool = False,
) -> Generator[type[T]]:
    """Gets all sub-classes of the root class."""
    if not skip_self and not (skip_abstract and inspect.isabstract(root)):
        yield root
    for leaf in root.__subclasses__():
        yield from list_all_subclasses(leaf, skip_self=False, skip_abstract=skip_abstract)


def find_syntax(
    likes: SyntaxLikes,
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> sublime.Syntax | None:
    """Finds the best syntax for one or more "Syntax object" / "scope" / "name" / "partial path"."""
    return first_true(find_syntaxes(likes, include_hidden=include_hidden, include_plaintext=include_plaintext))


def find_syntaxes(
    likes: SyntaxLikes,
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> tuple[sublime.Syntax, ...]:
    """Finds every syntax matching one or more "Syntax object" / "scope" / "name" / "partial path"."""
    # `_find_syntaxes()` is cached, so its arguments have to be hashable -- normalize here rather
    # than making "pass a tuple" a rule every caller has to know
    return _find_syntaxes(
        tuple(always_iterable(likes, base_type=(str, sublime.Syntax))),
        include_hidden=include_hidden,
        include_plaintext=include_plaintext,
    )


@clearable_lru_cache()
def _find_syntaxes(
    likes: tuple[SyntaxLike, ...],
    *,
    include_hidden: bool,
    include_plaintext: bool,
) -> tuple[sublime.Syntax, ...]:
    # a falsy "like" ("" or None from settings) matches nothing rather than everything.
    # The annotation is load-bearing: mypy can't solve `drop_falsy`'s `Iterable[T | None]`
    # against a union this wide and falls back to `object`, which then poisons the `map()`
    # and `filter()` below. Don't collapse this back into a walrus -- it can't be annotated.
    valid_likes: tuple[SyntaxLike, ...] = tuple(drop_falsy(likes))
    if not valid_likes:
        return ()

    all_syntaxes = get_sorted_syntaxes()

    def find_like(like: SyntaxLike) -> Generator[sublime.Syntax]:
        match like:
            case sublime.Syntax():
                yield like
            case str() if like.startswith("scope:"):
                yield from sublime.find_syntax_by_scope(like[6:])
            case str():
                like_cf = like.casefold()
                # by name
                yield from sublime.find_syntax_by_name(like)
                # by name (case-insensitive)
                yield from filter(lambda syntax: like_cf == get_syntax_name(syntax).casefold(), all_syntaxes)
                # by partial path
                yield from filter(lambda syntax: like in syntax.path, all_syntaxes)

    def filter_like(syntax: sublime.Syntax) -> bool:
        return (
            (include_hidden or not syntax.hidden)
            and (include_plaintext or not is_plaintext_syntax(syntax))
            # @see https://github.com/jfcherng-sublime/ST-AutoSetSyntax/issues/29
            # The "FileIcon" package uses dummy syntaxes just in order to set an icon in the sidebar.
            # We don't want to match those dummy syntaxes, so we filter them out.
            and ("/zzz A File Icon/" not in syntax.path)
        )

    # note that `unique_everseen` spans all `likes`, so a syntax reachable from two of them
    # is yielded once, in the order the earlier "like" found it
    return tuple(filter(filter_like, unique_everseen(chain.from_iterable(map(find_like, valid_likes)))))


@clearable_lru_cache()
def get_sorted_syntaxes() -> tuple[sublime.Syntax, ...]:
    """Gets all syntaxes, which are sorted by conventions."""

    def syntax_key(syntax: sublime.Syntax) -> tuple[int, ...]:
        """
        Compares syntaxes by

        - prefer `.sublime-syntax` over `.tmLanguage`
        - prefer non-hidden
        - prefer shorter path
        """
        ext = 0 if syntax.path.endswith(".sublime-syntax") else 1
        hidden = 1 if syntax.hidden else 0
        return (ext, hidden, len(syntax.path))

    return tuple(sorted(sublime.list_syntaxes(), key=syntax_key))


def extract_prefixed_dict[T](dict_: Mapping[str, T], *, prefix: str) -> dict[str, T]:
    """Extract dict with a prefix. The prefix will be removed from the key."""
    return {k[len(prefix) :]: v for k, v in dict_.items() if k.startswith(prefix)}


def head_tail_lines(content: str, n: int) -> str:
    """
    Return the first `n` lines and the last `n` lines of `content`, joined by a blank line.

    This is used to emulate how Vim/Emacs modelines are only recognized within the first/last
    few lines of a file rather than anywhere in the whole file content. A negative `n` means no
    limit, in which case `content` is returned as-is.
    """
    if n < 0:
        return content

    if n == 0:
        return ""

    first, last, overlapped = first_last_n_lines(content, n)

    if overlapped or not first:
        return content

    return "\n".join(first) + "\n\n" + "\n".join(last)


def head_tail_content_st(view: sublime.View, partial: int) -> str:
    if partial < 0:
        return view.substr(sublime.Region(0, view.size()))

    if (half := partial // 2) <= 0:
        return ""

    # not `<= half`: between `half` and `partial`, the head and the tail overlap, duplicating the middle
    if (size := view.size()) <= partial:
        return view.substr(sublime.Region(0, size))

    return (
        # for large files, most characteristics is at the beginning
        view.substr(sublime.Region(0, half))
        + "\n\n"
        # but some may be at the ending...
        + view.substr(sublime.Region(size - half, size))
    )


def first_last_n_lines(text: str, n: int) -> tuple[list[str], list[str], int]:
    """
    Get first/last n lines without materializing all lines.
    Assumes '\n' as the line separator (not universal newlines).

    Returns `(first, last, overlapped)`, where `overlapped` is how many lines are
    counted in both `first` and `last` (i.e., `text` has `2 * n` or fewer lines).
    """
    if n <= 0:
        return [], [], 0
    length = len(text)

    # First n lines (scan forward)
    first: list[str] = []
    pos = 0
    for _ in range(n):
        if pos >= length:
            break
        idx = text.find("\n", pos)
        if idx == -1:
            first.append(text[pos:])
            pos = length  # the trailing partial line consumed the rest of `text`
            break
        first.append(text[pos:idx])
        pos = idx + 1

    # Last n lines (scan backward). A line's start offset below `pos` means the
    # forward scan above already counted it, so tally that overlap on the fly
    # instead of collecting all offsets just to intersect them afterwards.
    last: list[str] = []
    overlapped = 0
    end = length
    has_more = length > 0
    if has_more and text[end - 1] == "\n":
        end -= 1
    for _ in range(n):
        if not has_more:
            break
        idx = text.rfind("\n", 0, end)
        if idx + 1 < pos:
            overlapped += 1
        last.append(text[idx + 1 : end])
        if idx == -1:
            has_more = False
        else:
            end = idx
    last.reverse()

    return first, last, overlapped


def is_plaintext_syntax(syntax: sublime.Syntax) -> bool:
    """Determinates whether the syntax is plain text."""
    return get_syntax_name(syntax) == "Plain Text"


def is_transient_view(view: sublime.View) -> bool:
    return bool(view.is_valid() and (sheet := view.sheet()) and sheet.is_transient())


def list_trimmed_filenames(filename: str, skip_self: bool = False) -> Generator[str]:
    """Generates trimmed filenames."""
    end = len(filename)
    if skip_self:
        end = filename.rfind(".", 0, end)
    while end > 0:
        yield filename[:end]
        end = filename.rfind(".", 0, end)


def list_trimmed_strings(string: str, suffixes: tuple[str, ...], skip_self: bool = False) -> Generator[str]:
    """Generates strings with suffixes trimmed."""
    trie = build_reversed_trie(suffixes)

    if not skip_self:
        yield string

    seen: set[str] = set()
    stack = [string[::-1]]
    while stack:
        string_rev = stack.pop()
        for prefix in trie.find_prefixes(string_rev):
            trimmed = string_rev[len(prefix) :]
            if trimmed not in seen:
                seen.add(trimmed)
                yield trimmed[::-1]
                stack.append(trimmed)


def str_finditer(content: str, substr: str) -> Generator[int]:
    def _() -> Generator[int]:
        idx = 0
        while (idx := content.find(substr, idx)) != -1:
            yield idx
            idx += len(substr)

    if substr == "":
        raise ValueError("substr cannot be an empty string (infinite loop)")
    yield from _()


def get_syntax_name(syntax: sublime.Syntax) -> str:
    """
    Gets syntax name with a workaround.

    @see https://github.com/sublimehq/sublime_text/issues/5560
    """
    return syntax.name or (Path(syntax.path).stem if syntax.path else "")


_RE_STRINGIFY_CLASS = re.compile(r"(<class '[^']+'>)")
_RE_STRINGIFY_ENUM = re.compile(r"<([._a-zA-Z]+): ('[^']+')>")
_RE_STRINGIFY_OBJ = re.compile(r"<([._a-zA-Z]+ [._a-zA-Z]+) at 0x[\dA-F]+>")


def stringify(obj: Any) -> str:
    """Custom object-to-string converter. Just used for debug messages."""
    if isinstance(obj, sublime.View):
        filepath = Path(filepath).as_posix() if (filepath := obj.file_name()) else ""
        return f'View({obj.id()}, "{filepath}")'

    r = repr(obj)
    r = _RE_STRINGIFY_CLASS.sub(r'"\1"', r)  # class
    r = _RE_STRINGIFY_ENUM.sub(r'"<\1(\2)>"', r)  # enum
    return _RE_STRINGIFY_OBJ.sub(r'"<\1>"', r)  # object
