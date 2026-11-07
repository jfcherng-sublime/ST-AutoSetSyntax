"""Tests for pure utility functions in plugin/utils.py."""

import random
import re
from abc import ABC
from abc import abstractmethod

import pytest

from plugin.utils import camel_to_snake
from plugin.utils import drop_falsy
from plugin.utils import ensure_trailing_newline
from plugin.utils import first_last_n_lines
from plugin.utils import get_fqcn
from plugin.utils import head_tail_lines
from plugin.utils import list_all_subclasses
from plugin.utils import list_trimmed_filenames
from plugin.utils import list_trimmed_strings
from plugin.utils import merge_literals_to_regex
from plugin.utils import merge_regexes
from plugin.utils import parse_regex_flags
from plugin.utils import str_finditer


@pytest.mark.parametrize(
    ("name", "expected"),
    [("CamelCase", "camel_case"), ("Foo", "foo"), ("foo", "foo"), ("FooBarBaz", "foo_bar_baz")],
)
def test_camel_to_snake(name, expected):
    assert camel_to_snake(name) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("hello\n", "hello\n"), ("hello", "hello\n"), ("", "\n"), (b"hello\n", b"hello\n"), (b"hello", b"hello\n")],
)
def test_ensure_trailing_newline(text, expected):
    assert ensure_trailing_newline(text) == expected


class TestMergeRegexes:
    def test_empty_returns_match_nothing(self):
        assert not re.search(merge_regexes([]), "anything")

    def test_single_regex_wrapped(self):
        result = merge_regexes(["foo"])
        assert re.search(result, "foobar")
        assert not re.search(result, "bar")

    def test_multiple_merged_as_alternation(self):
        result = merge_regexes(["foo", "bar"])
        assert re.search(result, "foo")
        assert re.search(result, "bar")
        assert not re.search(result, "baz")


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["IGNORECASE"], re.IGNORECASE),
        (["MULTILINE"], re.MULTILINE),
        (["IGNORECASE", "MULTILINE"], re.IGNORECASE | re.MULTILINE),
        (["NONEXISTENT_FLAG"], 0),
        (["I"], re.IGNORECASE),
        ([], 0),
    ],
)
def test_parse_regex_flags(flags, expected):
    assert parse_regex_flags(flags) == expected


class TestHeadTailLines:
    @pytest.mark.parametrize(
        ("content", "n", "expected"),
        [
            ("line1\nline2\nline3", 5, "line1\nline2\nline3"),
            ("line1\nline2\nline3", -1, "line1\nline2\nline3"),
            ("line1\nline2\nline3", 0, ""),
            ("a\nb\nc", 3, "a\nb\nc"),
            ("", 1, ""),
            ("\n", 1, "\n"),
            ("\n".join(f"line{i}" for i in range(1, 11)), 2, "line1\nline2\n\nline9\nline10"),
        ],
    )
    def test_trim(self, content, n, expected):
        assert head_tail_lines(content, n) == expected

    def test_modeline_in_the_middle_is_dropped(self):
        # A "vim:" line that only appears deep inside the body (e.g., inside a fenced code
        # block in a Markdown file) must not survive the head/tail trim.
        content = "\n".join([
            "# Title",
            "",
            "Some text",
            "",
            "```yaml",
            "# vim: set ft=yaml:",
            "key: value",
            "```",
            "",
            "More text",
        ])
        assert "vim:" not in head_tail_lines(content, 2)


class TestFirstLastNLines:
    @pytest.mark.parametrize(("text", "n"), [("a\nb\nc", 0), ("a\nb\nc", -1), ("", 3)])
    def test_non_positive_n_or_empty_text_returns_empty(self, text, n):
        assert first_last_n_lines(text, n) == ([], [], 0)

    def test_single_blank_line_fully_overlaps(self):
        # A lone trailing newline is one empty line, not two: `last` must not drop it.
        assert first_last_n_lines("\n", 1) == ([""], [""], 1)

    def test_fewer_lines_than_n_fully_overlaps(self):
        lines = ["line1", "line2", "line3"]
        assert first_last_n_lines("line1\nline2\nline3", 5) == (lines, lines, 3)

    def test_exact_n_lines_no_trailing_newline_fully_overlaps(self):
        # Regression: the last line has no trailing "\n", so the forward scan must still
        # mark the whole text as consumed instead of leaving the overlap boundary stale.
        assert first_last_n_lines("a\nb\nc", 3) == (["a", "b", "c"], ["a", "b", "c"], 3)

    def test_no_overlap_when_lines_exceed_2n(self):
        content = "\n".join(f"line{i}" for i in range(1, 11))
        assert first_last_n_lines(content, 2) == (["line1", "line2"], ["line9", "line10"], 0)

    def test_no_overlap_at_exact_2n_boundary(self):
        assert first_last_n_lines("l1\nl2\nl3\nl4", 2) == (["l1", "l2"], ["l3", "l4"], 0)


class TestFirstLastNLinesRandomized:
    """Cross-check first_last_n_lines() against a naive str.split("\\n")-based reference across
    many random texts/n. It deliberately avoids materializing all lines for performance (it backs
    VIM/Emacs modeline detection, where wrong line counting silently breaks the feature)."""

    @staticmethod
    def _naive_lines(text: str) -> list:
        if text == "":
            return []
        return text.removesuffix("\n").split("\n")

    def test_matches_naive_reference(self):
        for seed in range(30):
            rng = random.Random(seed)
            lines = ["".join(rng.choices("ab", k=rng.randint(0, 3))) for _ in range(rng.randint(0, 8))]
            text = "\n".join(lines)
            if lines and rng.random() < 0.5:
                text += "\n"

            naive = self._naive_lines(text)
            total = len(naive)

            for n in range(1, 6):
                first, last, overlapped = first_last_n_lines(text, n)

                assert first == naive[:n], (seed, text, n, "first")
                assert last == naive[max(0, total - n) :], (seed, text, n, "last")
                expected_overlap = len(set(range(min(n, total))) & set(range(max(0, total - n), total)))
                assert overlapped == expected_overlap, (seed, text, n, "overlap")


@pytest.mark.parametrize(
    ("filename", "skip_self", "expected"),
    [
        ("file.bak.tmp", False, ["file.bak.tmp", "file.bak", "file"]),
        ("file.bak.tmp", True, ["file.bak", "file"]),
        ("Makefile", False, ["Makefile"]),
        ("script.py", False, ["script.py", "script"]),
    ],
)
def test_list_trimmed_filenames(filename, skip_self, expected):
    assert list(list_trimmed_filenames(filename, skip_self=skip_self)) == expected


class TestStrFinditer:
    @pytest.mark.parametrize(
        ("text", "sub", "expected"),
        [("hello world", "world", [6]), ("ababab", "ab", [0, 2, 4]), ("hello", "xyz", [])],
    )
    def test_positions(self, text, sub, expected):
        assert list(str_finditer(text, sub)) == expected

    def test_empty_substr_raises(self):
        with pytest.raises(ValueError, match="empty string"):
            list(str_finditer("hello", ""))


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([1, None, 2, None, 3], [1, 2, 3]),
        (["a", "", "b"], ["a", "b"]),
        ([True, False, True], [True, True]),
        ([0, 1, 2], [1, 2]),
        ([], []),
    ],
)
def test_drop_falsy(items, expected):
    assert list(drop_falsy(items)) == expected


class TestGetFqcn:
    def test_none(self):
        assert get_fqcn(None) == "None"

    def test_class_object(self):
        assert get_fqcn(int) == "builtins.int"

    def test_instance(self):
        assert get_fqcn("hello") == "builtins.str"

    def test_custom_class(self):
        class Foo:
            pass

        assert get_fqcn(Foo()) == "test_utils.TestGetFqcn.test_custom_class.<locals>.Foo"


class TestMergeLiteralsToRegex:
    def test_multiple_literals(self):
        result = merge_literals_to_regex(["foo", "bar"])
        assert re.search(result, "foo")
        assert re.search(result, "bar")
        assert not re.search(result, "baz")

    def test_escapes_special_chars(self):
        result = merge_literals_to_regex(["foo.bar"])
        assert re.search(result, "foo.bar")
        assert not re.search(result, "fooXbar")

    def test_empty_input_matches_nothing(self):
        assert not re.search(merge_literals_to_regex([]), "anything")

    def test_one_literal_is_prefix_of_another(self):
        """A trie-compressed alternation (e.g. the vendored Triegex) can silently drop the
        longer word when one literal is a strict prefix of another -- both must still match."""
        result = merge_literals_to_regex(["sh", "shell"])
        assert re.search(result, "shell")
        assert re.search(result, "sh")
        assert not re.search(result, "python")

    def test_three_literals_with_shared_prefix(self):
        result = merge_literals_to_regex(["cc", "aab", "ccc"])
        assert re.search(result, "cc")
        assert re.search(result, "ccc")
        assert re.search(result, "aab")
        # a bare "c" must never match on its own -- it's not one of the literals
        assert not re.search(result, "cbabbc")


class _A:
    pass


class _B(_A):
    pass


class _C(_B):
    pass


class _D(_A):
    pass


class TestListAllSubclasses:
    def test_yields_self_by_default(self):
        assert _A in list(list_all_subclasses(_A))

    def test_skip_self_still_yields_every_descendant(self):
        result = list(list_all_subclasses(_A, skip_self=True))
        assert _A not in result
        assert {_B, _C, _D} <= set(result)

    def test_skip_abstract(self):
        class _Abstract(ABC):
            @abstractmethod
            def foo(self): ...

        class _Concrete(_Abstract):
            def foo(self): ...

        result = list(list_all_subclasses(_Abstract, skip_abstract=True))
        assert _Abstract not in result
        assert _Concrete in result

    def test_no_subclasses(self):
        class _Leaf:
            pass

        assert list(list_all_subclasses(_Leaf, skip_self=True)) == []


class TestListTrimmedStrings:
    def test_trim_suffixes(self):
        result = list(list_trimmed_strings("file.bak.tmp", (".bak", ".tmp")))
        assert {"file.bak.tmp", "file.bak", "file"} <= set(result)

    def test_skip_self(self):
        result = list(list_trimmed_strings("file.bak", (".bak",), skip_self=True))
        assert "file.bak" not in result
        assert "file" in result

    def test_no_suffixes(self):
        assert list(list_trimmed_strings("file", ())) == ["file"]

    def test_compound_suffix_trimming(self):
        result = list(list_trimmed_strings("file.min.js", (".min.js", ".js")))
        assert {"file.min.js", "file.min", "file"} <= set(result)
