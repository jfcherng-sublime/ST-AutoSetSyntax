from .lru_cache import clearable_lru_cache
from .settings import get_st_setting
from functools import cmp_to_key
from pathlib import Path
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
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

T = TypeVar("T")


def camel_to_snake(s: str) -> str:
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in s).lstrip("_")


@clearable_lru_cache()
def compile_regex(regex: Union[str, Pattern[str]], flags: int = 0) -> Pattern[str]:
    if isinstance(regex, Pattern):
        if regex.flags == flags:
            return regex
        regex = regex.pattern
    return re.compile(regex, flags)


@clearable_lru_cache()
def find_syntax_by_syntax_like(
    like: Union[str, sublime.Syntax],
    allow_hidden: bool = False,
    allow_plaintext: bool = True,
) -> Optional[sublime.Syntax]:
    if not like:
        return None

    def find_like(like: str) -> Iterable[sublime.Syntax]:
        # by scope
        if like.startswith("scope:"):
            return sublime.find_syntax_by_scope(like[6:])
        # by name
        if candidates := sublime.find_syntax_by_name(like):
            return candidates
        # by partial path
        return filter(lambda syntax: like in syntax.path, list_sorted_syntaxes())

    return first(
        (like,) if isinstance(like, sublime.Syntax) else find_like(like),
        lambda syntax: (allow_hidden or not syntax.hidden) and (allow_plaintext or not is_plaintext_syntax(syntax)),
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
    if not skip_self and not (skip_abstract and inspect.isabstract(root)):
        yield root
    for leaf in root.__subclasses__():
        yield from get_all_subclasses(leaf, skip_self=False, skip_abstract=skip_abstract)


def get_nth_item(items: Sequence[T], n: int, default: Optional[T] = None) -> Optional[T]:
    """Gets the `n`th item in `items`. Returns `default` if out of index."""
    return next(iter(items[n : n + 1]), default)


def is_plaintext_syntax(syntax: sublime.Syntax) -> bool:
    return syntax.name == "Plain Text"


def is_syntaxable_view(view: sublime.View, must_plaintext: bool = False) -> bool:
    return bool(
        view.is_valid()
        and not view.element()
        and not is_transient_view(view)
        and (not must_plaintext or ((syntax := view.syntax()) and is_plaintext_syntax(syntax)))
        and (not (size_max := get_st_setting("syntax_detection_size_limit", 0)) or size_max >= view.size())
    )


def is_transient_view(view: sublime.View) -> bool:
    # @see https://github.com/sublimehq/sublime_text/issues/4444
    # workaround for a transient view have no window right after it's loaded
    if not (window := view.window()):
        return True
    # @see https://forum.sublimetext.com/t/is-view-transient-preview-method/3247/2
    return view == window.transient_view_in_group(window.active_group())


@clearable_lru_cache()
def list_sorted_syntaxes() -> Tuple[sublime.Syntax, ...]:
    def syntax_cmp(a: sublime.Syntax, b: sublime.Syntax) -> int:
        """
        Order by

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


def parse_regex_flags(flags: Sequence[str]) -> int:
    """
    Valid flags are:
    `A`, `ASCII`, `DEBUG`, `I`, `IGNORECASE`, `L`, `LOCALE`, `M`, `MULTILINE`,
    `S`, `DOTALL`, `X`, `VERBOSE`, `U`, `UNICODE`.
    """
    if isinstance(flags, str):
        flags = (flags,)
    return sum(getattr(re, flag.upper(), 0) for flag in flags)


def removeprefix(s: str, prefix: str) -> str:
    return s[len(prefix) :] if s.startswith(prefix) else s


def removesuffix(s: str, suffix: str) -> str:
    # suffix="" should not call s[:-0]
    return s[: -len(suffix)] if suffix and s.endswith(suffix) else s


def snake_to_camel(s: str, upper_first: bool = True) -> str:
    first, *others = s.split("_")
    return first.title() if upper_first else first.lower() + "".join(map(str.title, others))


def stringify(obj: Any) -> str:
    """Custom object-to-string converter"""

    if isinstance(obj, sublime.View):
        if filepath := obj.file_name():
            filepath = Path(filepath).as_posix()
        else:
            filepath = ""

        return f'View({obj.id()}, "{filepath}")'

    r = repr(obj)
    r = compile_regex(r"(<class '[^']+'>)").sub(r'"\1"', r)
    r = compile_regex(r"<([._a-zA-Z]+ [._a-zA-Z]+) at 0x[\dA-F]+>").sub(r'"<\1>"', r)

    return r


def generate_trimmed_string(
    string: str,
    suffixes: Sequence[str],
    skip_self: bool = False,
) -> Generator[str, None, None]:
    if not skip_self:
        yield string

    for suffix in suffixes:
        if suffix and string.endswith(suffix):
            yield from generate_trimmed_string(
                string[: -len(suffix)],
                suffixes,
                skip_self=False,
            )
