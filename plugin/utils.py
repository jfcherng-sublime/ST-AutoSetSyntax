# This file is more self-sustained and shouldn't use things from other higher-level modules.

import inspect
import operator
import os
import re
import shutil
import stat
import tempfile
import threading
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from functools import cache
from functools import reduce
from functools import wraps
from pathlib import Path
from re import Pattern
from typing import Any

import sublime
from more_itertools import first_true
from more_itertools import unique_everseen

from ._vendor.trie import TrieNode
from ._vendor.triegex import Triegex
from .cache import clearable_lru_cache
from .types import SyntaxLike


def camel_to_snake(s: str) -> str:
    """Converts "CamelCase" to "snake_case"."""
    return "".join(f"_{c}" if c.isupper() else c for c in s).strip("_").lower()


def snake_to_camel(s: str, *, upper_first: bool = True) -> str:
    """Converts "snake_case" to "CamelCase"."""
    first, *others = s.split("_")
    return (first.title() if upper_first else first.lower()) + "".join(map(str.title, others))


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
    # this regex is enclosed by "(?:)"
    return Triegex(*map(re.escape, literals)).to_regex().replace(R"\b", "").replace(r"|~^(?#match nothing)", "")


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
def build_reversed_trie(words: tuple[str]) -> TrieNode:
    """Returns a trie with all words reversed. It can be used to match suffixes with reversed input string."""
    trie = TrieNode()
    for word in words:
        trie.insert(word[::-1])
    return trie


def debounce[T: Callable](time_s: float = 0.3) -> Callable[[T], T]:
    """
    Debounce a function so that it's called after `time_s` seconds.
    If it's called multiple times in the time frame, it will only run the last call.

    Taken and modified from https://github.com/salesforce/decorator-operations
    """

    def decorator(func: T) -> T:
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
        return debounced  # type: ignore[return-value]

    return decorator


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
        return (include_hidden or not syntax.hidden) and (include_plaintext or not is_plaintext_syntax(syntax))

    return tuple(filter(filter_like, unique_everseen(find_like(like))))


def find_syntaxes_by_syntax_likes(
    likes: Iterable[SyntaxLike],
    *,
    include_hidden: bool = False,
    include_plaintext: bool = True,
) -> Generator[sublime.Syntax]:
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


def resolve_window(obj: sublime.Buffer | sublime.View | sublime.Sheet | sublime.Window) -> sublime.Window | None:
    match obj:
        case sublime.Window():
            return obj
        case sublime.View() | sublime.Sheet():
            return obj.window()
        case sublime.Buffer():
            return obj.primary_view().window()
        case _:
            return None


def list_all_views(*, include_transient: bool = False) -> Generator[sublime.View]:
    for window in sublime.windows():
        yield from window.views(include_transient=include_transient)


def get_view_by_id(id: int) -> sublime.View | None:
    return view if (view := sublime.View(id)).is_valid() else None


def get_window_by_id(id: int) -> sublime.Window | None:
    return window if (window := sublime.Window(id)).is_valid() else None


def head_tail_content(content: str, partial: int) -> str:
    if partial < 0:
        return content

    if (half := partial // 2) <= 0:
        return ""

    if len(content) <= half:
        return content

    return content[:half] + "\n\n" + content[-half:]


def head_tail_content_st(view: sublime.View, partial: int) -> str:
    if partial < 0:
        return view.substr(sublime.Region(0, view.size()))

    if (half := partial // 2) <= 0:
        return ""

    if (size := view.size()) <= half:
        return view.substr(sublime.Region(0, size))

    return (
        # for large files, most characteristics is at the beginning
        view.substr(sublime.Region(0, half))
        + "\n\n"
        # but some may be at the ending...
        + view.substr(sublime.Region(size - half, size))
    )


def is_plaintext_syntax(syntax: sublime.Syntax) -> bool:
    """Determinates whether the syntax is plain text."""
    return get_syntax_name(syntax) == "Plain Text"


def is_transient_view(view: sublime.View) -> bool:
    return bool(view.is_valid() and (sheet := view.sheet()) and sheet.is_transient())


@cache
def get_expand_variable_map() -> dict[str, str]:
    cache_path = Path(sublime.cache_path())
    packages_path = Path(sublime.packages_path())

    paths: dict[str, Path] = {
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

    return {name: str(path.resolve()) for name, path in paths.items()}


def expand_variables[T: None | bool | int | float | str | dict | list | tuple](
    value: T,
    variables: dict[str, str] | None = None,
) -> T:
    return sublime.expand_variables(value, get_expand_variable_map() | (variables or {}))


def list_trimmed_filenames(filename: str, skip_self: bool = False) -> Generator[str]:
    """Generates trimmed filenames."""
    end = len(filename)
    if skip_self:
        end = filename.rfind(".", 0, end)
    while end > 0:
        yield filename[:end]
        end = filename.rfind(".", 0, end)


def list_trimmed_strings(string: str, suffixes: tuple[str], skip_self: bool = False) -> Generator[str]:
    """Generates strings with suffixes trimmed."""
    trie = build_reversed_trie(suffixes)

    def dfs(string_rev: str) -> Generator[str]:
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


def str_finditer(content: str, substr: str) -> Generator[int]:
    def _() -> Generator[int]:
        idx = 0
        while (idx := content.find(substr, idx)) != -1:
            yield idx
            idx += len(substr)

    if substr == "":
        raise ValueError("substr cannot be an empty string (infinite loop)")
    yield from _()


def rmtree_ex(path: str | Path, ignore_errors: bool = False) -> None:
    """
    Remove the given recursively.

    :note: we use shutil rmtree but adjust its behaviour to see whether files that
        couldn't be deleted are read-only. Windows will not remove them in that case

    @see https://github.com/gitpython-developers/GitPython/blob/ea43defd777a9c0751fc44a9c6a622fc2dbd18a0/git/util.py#L101-L118
    """
    if os.name == "nt" and (path := Path(path)).is_absolute():
        path = Rf"\\?\{path}"  # use UNC path to resolve Windows long path issue

    def onexc(func: Callable, path: str | Path, exec_info: Any) -> None:
        try:
            os.chmod(path, stat.S_IWUSR)
            func(path)  # will scream if still not possible to delete.
        except Exception:
            if not ignore_errors:
                raise

    return shutil.rmtree(path, False, onexc=onexc)


def get_syntax_name(syntax: sublime.Syntax) -> str:
    """
    Gets syntax name with a workaround.

    @see https://github.com/sublimehq/sublime_text/issues/5560
    """
    return syntax.name or (Path(syntax.path).stem if syntax.path else "")


def stringify(obj: Any) -> str:
    """Custom object-to-string converter. Just used for debug messages."""
    if isinstance(obj, sublime.View):
        filepath = Path(filepath).as_posix() if (filepath := obj.file_name()) else ""
        return f'View({obj.id()}, "{filepath}")'

    r = repr(obj)
    r = compile_regex(r"(<class '[^']+'>)").sub(r'"\1"', r)  # class
    r = compile_regex(r"<([._a-zA-Z]+): ('[^']+')>").sub(r'"<\1(\2)>"', r)  # enum
    r = compile_regex(r"<([._a-zA-Z]+ [._a-zA-Z]+) at 0x[\dA-F]+>").sub(r'"<\1>"', r)  # object

    return r
