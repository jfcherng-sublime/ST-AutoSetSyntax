# This file is more self-sustained and shouldn't use things from other higher-level modules.
from __future__ import annotations

import inspect
import operator
import re
import sys
import tempfile
import threading
from functools import cmp_to_key, lru_cache, reduce, wraps
from itertools import islice
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterable, List, Pattern, Tuple, TypeVar, Union, cast, overload

import sublime

from .cache import clearable_lru_cache
from .libs.trie import TrieNode
from .types import SemanticVersion, SyntaxLike

_T = TypeVar("_T")
_U = TypeVar("_U")

_T_Callable = TypeVar("_T_Callable", bound=Callable[..., Any])
_T_ExpandableVar = TypeVar("_T_ExpandableVar", bound=Union[None, bool, int, float, str, Dict, List, Tuple])


def camel_to_snake(s: str) -> str:
    """Converts "CamelCase" to "snake_case"."""
    return "".join(f"_{c}" if c.isupper() else c for c in s).strip("_").lower()


def snake_to_camel(s: str, upper_first: bool = True) -> str:
    """Converts "snake_case" to "CamelCase"."""
    first, *others = s.split("_")
    return (first.title() if upper_first else first.lower()) + "".join(map(str.title, others))


if sys.version_info >= (3, 9):
    remove_prefix = str.removeprefix
    remove_suffix = str.removesuffix
else:

    def remove_prefix(s: str, prefix: str) -> str:
        """Remove the prefix from the string. I.e., str.removeprefix in Python 3.9."""
        return s[len(prefix) :] if s.startswith(prefix) else s

    def remove_suffix(s: str, suffix: str) -> str:
        """Remove the suffix from the string. I.e., str.removesuffix in Python 3.9."""
        # suffix="" should not call s[:-0]
        return s[: -len(suffix)] if suffix and s.endswith(suffix) else s


@clearable_lru_cache()
def compile_regex(regex: str | Pattern[str], flags: int = 0) -> Pattern[str]:
    """Compile the regex string/object into a object with the given flags."""
    if isinstance(regex, Pattern):
        if regex.flags == flags:
            return regex
        regex = regex.pattern
    return re.compile(regex, flags)


def merge_literals_to_regex(literals: Iterable[str]) -> str:
    """
    Merge (non-regex) literal strings into an optimized regex string.

    The returned regex is enclosed as `(?:...)`.
    """
    from .libs.triegex import Triegex

    # this regex is enclosed by "(?:)"
    return (
        Triegex(*map(re.escape, literals))  # type: ignore
        .to_regex()
        .replace(r"\b", "")  # type: ignore
        .replace(r"|~^(?#match nothing)", "")
    )


def merge_regexes(regexes: Iterable[str]) -> str:
    """Merge regex strings into a single regex string."""
    if not (regexes := tuple(regexes)):
        return ""

    merged = "(?:" + ")|(?:".join(regexes) + ")" if len(regexes) > 1 else regexes[0]
    return f"(?:{merged})"


def parse_regex_flags(flags: Iterable[str]) -> int:
    """
    Parse string regex flags into an int value.

    Valid flags are:
    `A`, `ASCII`, `DEBUG`, `I`, `IGNORECASE`, `L`, `LOCALE`, `M`, `MULTILINE`,
    `S`, `DOTALL`, `X`, `VERBOSE`, `U`, `UNICODE`.

    @see https://docs.python.org/3.8/library/re.html#re.A
    """
    if isinstance(flags, str):
        flags = (flags,)
    return reduce(operator.ior, (getattr(re, flag, 0) for flag in flags), 0)


@clearable_lru_cache()
def build_reversed_trie(words: tuple[str]) -> TrieNode:
    """Returns a trie with all words reversed. It can be used to match suffixes with reversed input string."""
    trie = TrieNode()
    for word in words:
        trie.insert(word[::-1])
    return trie


def debounce(time_s: float = 0.3) -> Callable[[_T_Callable], _T_Callable]:
    """
    Debounce a function so that it's called after `time_s` seconds.
    If it's called multiple times in the time frame, it will only run the last call.

    Taken and modified from https://github.com/salesforce/decorator-operations
    """

    def decorator(func: _T_Callable) -> _T_Callable:
        @wraps(func)
        def debounced(*args: Any, **kwargs: Any) -> None:
            def call_function() -> Any:
                delattr(debounced, "_timer")
                return func(*args, **kwargs)

            if timer := getattr(debounced, "_timer", None):
                timer.cancel()

            timer = threading.Timer(time_s, call_function)
            timer.start()
            setattr(debounced, "_timer", timer)

        setattr(debounced, "_timer", None)
        return cast(_T_Callable, debounced)

    return decorator


@overload
def first_true(
    items: Iterable[_T],
    default: _U,
    pred: Callable[[_T], bool] | None = None,
) -> _T | _U:
    ...


@overload
def first_true(
    items: Iterable[_T],
    *,
    pred: Callable[[_T], bool] | None = None,
) -> _T | None:
    ...


def first_true(
    items: Iterable[_T],
    default: _U | None = None,
    pred: Callable[[_T], bool] | None = None,
) -> _T | _U | None:
    """
    Gets the first item which satisfies the `pred`. Otherwise, `default`.
    If `pred` is not given or `None`, the first truthy item will be returned.
    """
    return next(filter(pred, items), default)


def list_all_subclasses(
    root: type[_T],
    skip_abstract: bool = False,
    skip_self: bool = False,
) -> Generator[type[_T], None, None]:
    """Gets all sub-classes of the root class."""
    if not skip_self and not (skip_abstract and inspect.isabstract(root)):
        yield root
    for leaf in root.__subclasses__():
        yield from list_all_subclasses(leaf, skip_self=False, skip_abstract=skip_abstract)


@overload
def nth(items: Iterable[_T], n: int) -> _T | None:
    ...


@overload
def nth(items: Iterable[_T], n: int, default: _U) -> _T | _U:
    ...


def nth(items: Iterable[_T], n: int, default: _U | None = None) -> _T | _U | None:
    """Gets the `n`th item (started from 0th) in `items`. Returns `default` if no such item."""
    return next(islice(iter(items), n, None), default)


def stable_unique(items: Iterable[_T]) -> Generator[_T, None, None]:
    """Lists unique items from the iterable, in their original order."""
    yield from {item: True for item in items}.keys()


@clearable_lru_cache()
def find_syntax_by_syntax_like(
    like: SyntaxLike,
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> sublime.Syntax | None:
    """Finds a syntax by a "Syntax object" / "scope" / "name" / "partial path"."""
    return first_true(
        find_syntaxes_by_syntax_like(
            like,
            include_hidden=include_hidden,
            include_plaintext=include_plaintext,
        ),
    )


def find_syntax_by_syntax_likes(
    likes: Iterable[SyntaxLike],
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> sublime.Syntax | None:
    """Finds a syntax by an Iterable of "Syntax object" / "scope" / "name" / "partial path"."""
    return first_true(
        find_syntaxes_by_syntax_likes(
            likes,
            include_hidden=include_hidden,
            include_plaintext=include_plaintext,
        ),
    )


@clearable_lru_cache()
def find_syntaxes_by_syntax_like(
    like: SyntaxLike,
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> tuple[sublime.Syntax, ...]:
    """Finds syntaxes by a "Syntax object" / "scope" / "name" / "partial path"."""
    if not like:
        return tuple()

    all_syntaxes = get_sorted_syntaxes()

    def find_like(like: SyntaxLike) -> Generator[sublime.Syntax, None, None]:
        if isinstance(like, sublime.Syntax):
            yield like
            return

        # by scope
        if like.startswith("scope:"):
            yield from sublime.find_syntax_by_scope(like[6:])
            return

        like_cf = like.casefold()

        # by name
        yield from sublime.find_syntax_by_name(like)
        # by name (case-insensitive)
        yield from filter(lambda syntax: like_cf == syntax.name.casefold(), all_syntaxes)
        # by partial path
        yield from filter(lambda syntax: like in syntax.path, all_syntaxes)  # type: ignore

    def filter_like(syntax: sublime.Syntax) -> bool:
        return (include_hidden or not syntax.hidden) and (include_plaintext or not is_plaintext_syntax(syntax))

    return tuple(filter(filter_like, stable_unique(find_like(like))))


def find_syntaxes_by_syntax_likes(
    likes: Iterable[SyntaxLike],
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> Generator[sublime.Syntax, None, None]:
    """Finds syntaxes by an Iterable of "Syntax object" / "scope" / "name" / "partial path"."""
    for like in likes:
        yield from find_syntaxes_by_syntax_like(
            like,
            include_hidden=include_hidden,
            include_plaintext=include_plaintext,
        )


@clearable_lru_cache()
def get_sorted_syntaxes() -> tuple[sublime.Syntax, ...]:
    """Gets all syntaxes, which are sorted by conventions."""

    def syntax_cmp(a: sublime.Syntax, b: sublime.Syntax) -> int:
        """
        Compares syntaxes by

        - prefer `.sublime-syntax` over `.tmLanguage`
        - prefer non-hidden
        - prefer shorter path
        """
        if (ext_a := Path(a.path).suffix) != Path(b.path).suffix:
            return -1 if ext_a == ".sublime-syntax" else 1
        if (hidden_a := a.hidden) != b.hidden:
            return 1 if hidden_a else -1
        return len(a.path) - len(b.path)

    return tuple(sorted(sublime.list_syntaxes(), key=cmp_to_key(syntax_cmp)))


def resolve_window(obj: Any) -> sublime.Window | None:
    if isinstance(obj, sublime.Window):
        return obj
    window = None
    if isinstance(obj, (sublime.View, sublime.Sheet)):
        window = obj.window()
    return window


def list_all_views(*, include_transient: bool = False) -> Generator[sublime.View, None, None]:
    for window in sublime.windows():
        yield from window.views(include_transient=include_transient)


def get_view_by_id(id: int) -> sublime.View | None:
    return first_true(list_all_views(include_transient=True), pred=lambda view: view.id() == id)


def head_tail_content(content: str, partial: int) -> str:
    if (half := partial // 2) <= 0:
        return ""

    if len(content) <= partial:
        return content

    return content[:half] + "\n\n" + content[-half:]


def head_tail_content_st(view: sublime.View, partial: int) -> str:
    if (half := partial // 2) <= 0:
        return ""

    if (size := view.size()) <= partial:
        return view.substr(sublime.Region(0, size))

    return (
        # for large files, most characteristics is in the starting
        view.substr(sublime.Region(0, half))
        + "\n\n"
        # but some may be in the ending...
        + view.substr(sublime.Region(size - half, size))
    )


def is_plaintext_syntax(syntax: sublime.Syntax) -> bool:
    """Determinates whether the syntax is plain text."""
    return syntax.name == "Plain Text"


def is_transient_view(view: sublime.View) -> bool:
    return bool(view.is_valid() and (sheet := view.sheet()) and sheet.is_transient())


@lru_cache
def get_expand_variable_map() -> dict[str, str]:
    cache_path = Path(sublime.cache_path())
    packages_path = Path(sublime.packages_path())

    paths = {
        # from OS
        "home": Path.home(),
        "temp_dir": Path(tempfile.gettempdir()),
        # from ST itself
        "bin": Path(sublime.executable_path()).parent,
        "cache": cache_path,
        "data": packages_path.parent,
        "index": cache_path.parent / "Index",
        "installed_packages": Path(sublime.installed_packages_path()),
        "lib": packages_path.parent / "Lib",
        "local": packages_path.parent / "Local",
        "log": packages_path.parent / "Log",
        "packages": packages_path,
        # from LSP
        "package_storage": cache_path.parent / "Package Storage",
    }

    def find_latest_lsp_utils_node(package_storage: Path) -> tuple[Path, SemanticVersion] | None:
        def list_node_versions(folder: Path) -> Generator[SemanticVersion, None, None]:
            for path in folder.iterdir() if folder.is_dir() else []:
                if (
                    path.is_dir()
                    and (m := re.fullmatch(r"\d+\.\d+\.\d+", path.name))
                    and (version := SemanticVersion.from_str(m.group(0)))
                ):
                    yield version

        base_dir = package_storage / "lsp_utils/node-runtime"
        if not (version := max(list_node_versions(base_dir), default=None)):
            return None

        return (base_dir, version)

    def get_node_path_candidates(node_version_dir: Path) -> Generator[Path, None, None]:
        yield node_version_dir / "Electron.app/Contents/MacOS/Electron"  # Electron (Linux)
        yield node_version_dir / "electron"  # Electron (Linux)
        yield node_version_dir / "electron.exe"  # Electron (Windows)
        yield node_version_dir / "node/bin/node"  # Node.js (Linux & Mac)
        yield node_version_dir / "node/node.exe"  # Node.js (Windows)

    def get_node_path(node_version_dir: Path) -> Path | None:
        return first_true(
            get_node_path_candidates(node_version_dir),
            pred=lambda path: bool(path and path.is_file()),
        )

    if node_info := find_latest_lsp_utils_node(paths["package_storage"]):
        node_version_dir = node_info[0] / str(node_info[1])
        paths["lsp_utils_node_bin"] = get_node_path(node_version_dir) or Path("LSP_UTILS_NODE_NOT_FOUND")

    return {name: str(path.resolve()) for name, path in paths.items()}


def expand_variables(value: _T_ExpandableVar, variables: dict[str, str] | None = None) -> _T_ExpandableVar:
    return sublime.expand_variables(value, {**get_expand_variable_map(), **(variables or {})})


def list_trimmed_filenames(filename: str, skip_self: bool = False) -> Generator[str, None, None]:
    """Generates trimmed filenames."""
    end = len(filename)
    if skip_self:
        end = filename.rfind(".", 0, end)
    while end > 0:
        yield filename[:end]
        end = filename.rfind(".", 0, end)


def list_trimmed_strings(string: str, suffixes: tuple[str], skip_self: bool = False) -> Generator[str, None, None]:
    """Generates strings with suffixes trimmed."""
    trie = build_reversed_trie(suffixes)

    def dfs(string_rev: str) -> Generator[str, None, None]:
        for prefix in trie.find_prefixes(string_rev):
            yield (trimmed := string_rev[len(prefix) :])
            yield from dfs(trimmed)

    if not skip_self:
        yield string

    results: set[str] = set()
    for trimmed in dfs(string[::-1]):
        if trimmed not in results:
            results.add(trimmed)
            yield trimmed[::-1]


def str_finditer(content: str, substr: str) -> Generator[int, None, None]:
    idx = 0
    while (idx := content.find(substr, idx)) != -1:
        yield idx
        idx += len(substr)


def stringify(obj: Any) -> str:
    """Custom object-to-string converter. Just used for debug messages."""
    if isinstance(obj, sublime.View):
        if filepath := obj.file_name():
            filepath = Path(filepath).as_posix()
        else:
            filepath = ""

        return f'View({obj.id()}, "{filepath}")'

    r = repr(obj)
    r = compile_regex(r"(<class '[^']+'>)").sub(r'"\1"', r)  # class
    r = compile_regex(r"<([._a-zA-Z]+): ('[^']+')>").sub(r'"<\1(\2)>"', r)  # enum
    r = compile_regex(r"<([._a-zA-Z]+ [._a-zA-Z]+) at 0x[\dA-F]+>").sub(r'"<\1>"', r)  # object

    return r
