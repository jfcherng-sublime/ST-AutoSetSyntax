from .lru_cache import clearable_lru_cache
from .settings import get_st_setting
from .types import SyntaxLike
from functools import cmp_to_key
from functools import lru_cache
from functools import reduce
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)
import inspect
import re
import sublime
import tempfile

T = TypeVar("T")
ExpandableVar = TypeVar("ExpandableVar", None, bool, int, float, str, Dict, List, Tuple)


def camel_to_snake(s: str) -> str:
    """Converts "CamelCase" to "snake_case"."""
    return "".join(f"_{c}" if c.isupper() else c for c in s).strip("_").lower()


@clearable_lru_cache()
def compile_regex(regex: Union[str, Pattern[str]], flags: int = 0) -> Pattern[str]:
    """Compile the regex string/object into a object with the given flags."""
    if isinstance(regex, Pattern):
        if regex.flags == flags:
            return regex
        regex = regex.pattern
    return re.compile(regex, flags)


@clearable_lru_cache()
def find_syntax_by_syntax_like(
    like: SyntaxLike,
    *,
    allow_hidden: bool = False,
    allow_plaintext: bool = True,
) -> Optional[sublime.Syntax]:
    """Find a syntax by a "Syntax object" / "scope" / "name" / "partial path"."""
    return first(find_syntaxes_by_syntax_like(like, allow_hidden=allow_hidden, allow_plaintext=allow_plaintext))


def find_syntax_by_syntax_likes(
    likes: Iterable[SyntaxLike],
    *,
    allow_hidden: bool = False,
    allow_plaintext: bool = True,
) -> Optional[sublime.Syntax]:
    """Find a syntax by a Iterable of "Syntax object" / "scope" / "name" / "partial path"."""
    return first(
        find_syntax_by_syntax_like(
            like,
            allow_hidden=allow_hidden,
            allow_plaintext=allow_plaintext,
        )
        for like in likes
    )


@clearable_lru_cache()
def find_syntaxes_by_syntax_like(
    like: SyntaxLike,
    *,
    allow_hidden: bool = False,
    allow_plaintext: bool = True,
) -> Tuple[sublime.Syntax, ...]:
    """Find syntaxes by a "Syntax object" / "scope" / "name" / "partial path"."""
    if not like:
        return tuple()

    def find_like(like: str) -> Iterable[sublime.Syntax]:
        like_lower = like.lower()
        all_syntaxes: Tuple[sublime.Syntax, ...] = list_sorted_syntaxes()
        candidates: Iterable[sublime.Syntax]

        # by scope
        if like.startswith("scope:"):
            return sublime.find_syntax_by_scope(like[6:])
        # by name
        if candidates := sublime.find_syntax_by_name(like):
            return candidates
        # by name (case-insensitive)
        if candidates := tuple(filter(lambda syntax: like_lower == syntax.name.lower(), all_syntaxes)):
            return candidates
        # by partial path
        if candidates := tuple(filter(lambda syntax: like in syntax.path, all_syntaxes)):
            return candidates
        # nothing found
        return tuple()

    return tuple(
        syntax
        for syntax in ((like,) if isinstance(like, sublime.Syntax) else find_like(like))
        if (allow_hidden or not syntax.hidden) and (allow_plaintext or not is_plaintext_syntax(syntax))
    )


def first(
    items: Iterable[T],
    test: Optional[Callable[[T], bool]] = None,
    default: Optional[T] = None,
) -> Optional[T]:
    """
    Gets the first item which satisfies the `test`. Otherwise, `default`.
    If `test` is not given or `None`, the first truthy item will be returned.
    """
    return next(filter(test, items), default)


def get_all_subclasses(
    root: Type[T],
    skip_abstract: bool = False,
    skip_self: bool = False,
) -> Generator[Type[T], None, None]:
    """Gets all sub-classes of the root class."""
    if not skip_self and not (skip_abstract and inspect.isabstract(root)):
        yield root
    for leaf in root.__subclasses__():
        yield from get_all_subclasses(leaf, skip_self=False, skip_abstract=skip_abstract)  # type: ignore


def get_nth_item(items: Sequence[T], n: int, default: Optional[T] = None) -> Optional[T]:
    """Gets the `n`th item in `items`. Returns `default` if out of index."""
    return next(iter(items[n : n + 1]), default)


def get_st_window(
    obj: Union[sublime.View, sublime.Sheet, sublime.Window],
    fallback: bool = False,
) -> Optional[sublime.Window]:
    if isinstance(obj, sublime.Window):
        return obj
    window = None
    if isinstance(obj, (sublime.View, sublime.Sheet)):
        window = obj.window()
    return window or (sublime.active_window() if fallback else None)


def get_view_by_id(id: int) -> Optional[sublime.View]:
    for window in sublime.windows():
        for view in window.views():
            if view.id() == id:
                return view
    return None


def head_tail_content(content: str, partial: int) -> str:
    if partial < 0:
        return ""

    if len(content) <= partial * 2:
        return content

    return content[:partial] + "\n\n" + content[-partial:]


def head_tail_content_st(view: sublime.View, partial: int) -> str:
    if partial < 0:
        return ""

    if (size := view.size()) <= partial * 2:
        return view.substr(sublime.Region(0, size))

    return (
        # for large files, most characteristics is in the starting
        view.substr(sublime.Region(0, partial))
        + "\n\n"
        # but some may be in the ending...
        + view.substr(sublime.Region(size - partial, size))
    )


def is_plaintext_syntax(syntax: sublime.Syntax) -> bool:
    """Determinates whether the syntax is plain text."""
    return syntax.name == "Plain Text"


def is_syntaxable_view(view: sublime.View, must_plaintext: bool = False) -> bool:
    """Determinates whether the view is what we want to set a sytnax on."""
    return bool(
        view.is_valid()
        and not view.element()
        and not is_transient_view(view)
        and (not must_plaintext or ((syntax := view.syntax()) and is_plaintext_syntax(syntax)))
        and (not (size_max := get_st_setting("syntax_detection_size_limit", 0)) or size_max >= view.size())
    )


def is_transient_view(view: sublime.View) -> bool:
    """Determinates whether the view is a transient one such as a "Goto Anything" preview."""
    # @see https://github.com/sublimehq/sublime_text/issues/4444
    # workaround for a transient view have no window right after it's loaded
    if not (window := view.window()):
        return True
    # @see https://forum.sublimetext.com/t/is-view-transient-preview-method/3247/2
    return view == window.transient_view_in_group(window.active_group())


@clearable_lru_cache()
def list_sorted_syntaxes() -> Tuple[sublime.Syntax, ...]:
    """Lists all syntaxes in a tuple, which is sorted by conventions."""

    def syntax_cmp(a: sublime.Syntax, b: sublime.Syntax) -> int:
        """
        Order syntaxes by

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


def merge_literals_to_regex(literals: Iterable[str]) -> str:
    """Merge (non-regex) literal strings into an optimized regex string."""
    from .libs.triegex import Triegex

    regex = (
        Triegex(*map(re.escape, literals))  # type: ignore
        .to_regex()
        .replace(r"\b", "")  # type: ignore
        .replace(r"|~^(?#match nothing)", "")
    )

    return regex  # this regex is enclosed by "(?:)"


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
    return reduce(
        lambda carry, element: carry | element,
        (int(getattr(re, flag, 0)) for flag in flags),
    )


def remove_prefix(s: str, prefix: str) -> str:
    """Remove the prefix from the string. I.e., str.removeprefix in Python 3.9."""
    return s[len(prefix) :] if s.startswith(prefix) else s


def remove_suffix(s: str, suffix: str) -> str:
    """Remove the suffix from the string. I.e., str.removesuffix in Python 3.9."""
    # suffix="" should not call s[:-0]
    return s[: -len(suffix)] if suffix and s.endswith(suffix) else s


def snake_to_camel(s: str, upper_first: bool = True) -> str:
    """Converts "snake_case" to "CamelCase"."""
    first, *others = s.split("_")
    return first.title() if upper_first else first.lower() + "".join(map(str.title, others))


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


def generate_trimmed_strings(
    string: str,
    suffixes: Sequence[str],
    skip_self: bool = False,
) -> Generator[str, None, None]:
    """Generates strings with suffixes trimmed."""
    if not skip_self:
        yield string

    for suffix in suffixes:
        if suffix and string.endswith(suffix):
            yield from generate_trimmed_strings(
                string[: -len(suffix)],
                suffixes,
                skip_self=False,
            )


@lru_cache
def get_expand_variable_map() -> Dict[str, str]:
    cache_path = Path(sublime.cache_path())
    packages_path = Path(sublime.packages_path())

    paths = {
        # from OS
        "home": Path.home(),
        "temp_dir": Path(tempfile.gettempdir()),
        # from ST itself
        "bin": Path(sublime.executable_path()).parent,
        "cache": cache_path,
        "data": packages_path / "..",
        "index": cache_path / ".." / "Index",
        "installed_packages": Path(sublime.installed_packages_path()),
        "lib": packages_path / ".." / "Lib",
        "local": packages_path / ".." / "Local",
        "log": packages_path / ".." / "Log",
        "packages": packages_path,
        # from LSP
        "package_storage": cache_path / ".." / "Package Storage",
    }

    def _find_latest_lsp_utils_node_version(package_storage: Path) -> Optional[Tuple[int, int, int]]:
        if not (base_dir := package_storage / "lsp_utils/node-runtime").is_dir():
            return None

        version: Tuple[int, int, int] = (-1, -1, -1)
        for path in base_dir.iterdir():
            if path.is_dir() and (m := re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", path.name)):
                version = max(version, (int(m.group(1)), int(m.group(2)), int(m.group(3))))
        return version if version[0] != -1 else None

    if node_version := _find_latest_lsp_utils_node_version(paths["package_storage"]):
        node_version_str = ".".join(map(str, node_version))
        node_exe = "node.exe" if sublime.platform() == "windows" else "node"
        paths["lsp_utils_node_dir"] = paths["package_storage"] / f"lsp_utils/node-runtime/{node_version_str}/node"
        paths["lsp_utils_node_bin"] = paths["lsp_utils_node_dir"] / node_exe

    return {name: str(path.resolve()) for name, path in paths.items()}


def expand_variables(value: ExpandableVar, variables: Optional[Dict[str, str]] = None) -> ExpandableVar:
    return sublime.expand_variables(value, {**get_expand_variable_map(), **(variables or {})})
