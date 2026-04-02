"""Tests for pure utility functions in plugin/utils.py."""

import re

import pytest

# ── camel_to_snake ────────────────────────────────────────────────────────────


class TestCamelToSnake:
    def test_basic_camel(self):
        from plugin.utils import camel_to_snake

        assert camel_to_snake("CamelCase") == "camel_case"

    def test_single_word(self):
        from plugin.utils import camel_to_snake

        assert camel_to_snake("Foo") == "foo"

    def test_already_lower(self):
        from plugin.utils import camel_to_snake

        assert camel_to_snake("foo") == "foo"

    def test_three_words(self):
        from plugin.utils import camel_to_snake

        assert camel_to_snake("FooBarBaz") == "foo_bar_baz"

    def test_constraint_suffix_trimming(self):
        # The convention used in AbstractConstraint.name() is:
        #   camel_to_snake("FooBarConstraint".removesuffix("Constraint")) == "foo_bar"
        from plugin.utils import camel_to_snake

        assert camel_to_snake("FooBarConstraint".removesuffix("Constraint")) == "foo_bar"

    def test_match_suffix_trimming(self):
        from plugin.utils import camel_to_snake

        assert camel_to_snake("AnyMatch".removesuffix("Match")) == "any"


# ── snake_to_camel ────────────────────────────────────────────────────────────


class TestSnakeToCamel:
    def test_basic(self):
        from plugin.utils import snake_to_camel

        assert snake_to_camel("snake_case") == "SnakeCase"

    def test_upper_first_false(self):
        from plugin.utils import snake_to_camel

        assert snake_to_camel("foo_bar", upper_first=False) == "fooBar"

    def test_single_word(self):
        from plugin.utils import snake_to_camel

        assert snake_to_camel("foo") == "Foo"

    def test_three_parts(self):
        from plugin.utils import snake_to_camel

        assert snake_to_camel("foo_bar_baz") == "FooBarBaz"


# ── ensure_trailing_newline ───────────────────────────────────────────────────


class TestEnsureTrailingNewline:
    def test_str_already_has_newline(self):
        from plugin.utils import ensure_trailing_newline

        assert ensure_trailing_newline("hello\n") == "hello\n"

    def test_str_no_newline(self):
        from plugin.utils import ensure_trailing_newline

        assert ensure_trailing_newline("hello") == "hello\n"

    def test_empty_str(self):
        from plugin.utils import ensure_trailing_newline

        assert ensure_trailing_newline("") == "\n"

    def test_bytes_already_has_newline(self):
        from plugin.utils import ensure_trailing_newline

        assert ensure_trailing_newline(b"hello\n") == b"hello\n"

    def test_bytes_no_newline(self):
        from plugin.utils import ensure_trailing_newline

        assert ensure_trailing_newline(b"hello") == b"hello\n"


# ── merge_regexes ─────────────────────────────────────────────────────────────


class TestMergeRegexes:
    def test_empty_returns_match_nothing(self):
        from plugin.utils import merge_regexes

        result = merge_regexes([])
        # Should never match anything
        assert not re.search(result, "anything")

    def test_single_regex_wrapped(self):
        from plugin.utils import merge_regexes

        result = merge_regexes(["foo"])
        assert re.search(result, "foobar")
        assert not re.search(result, "bar")

    def test_multiple_merged_as_alternation(self):
        from plugin.utils import merge_regexes

        result = merge_regexes(["foo", "bar"])
        assert re.search(result, "foo")
        assert re.search(result, "bar")
        assert not re.search(result, "baz")


# ── parse_regex_flags ─────────────────────────────────────────────────────────


class TestParseRegexFlags:
    def test_ignorecase(self):
        from plugin.utils import parse_regex_flags

        assert parse_regex_flags(["IGNORECASE"]) == re.IGNORECASE

    def test_multiline(self):
        from plugin.utils import parse_regex_flags

        assert parse_regex_flags(["MULTILINE"]) == re.MULTILINE

    def test_multiple_flags(self):
        from plugin.utils import parse_regex_flags

        result = parse_regex_flags(["IGNORECASE", "MULTILINE"])
        assert result == (re.IGNORECASE | re.MULTILINE)

    def test_invalid_flag_returns_zero(self):
        from plugin.utils import parse_regex_flags

        assert parse_regex_flags(["NONEXISTENT_FLAG"]) == 0

    def test_short_alias(self):
        from plugin.utils import parse_regex_flags

        assert parse_regex_flags(["I"]) == re.IGNORECASE

    def test_empty(self):
        from plugin.utils import parse_regex_flags

        assert parse_regex_flags([]) == 0


# ── head_tail_content ─────────────────────────────────────────────────────────


class TestHeadTailContent:
    def test_short_content_returned_as_is(self):
        from plugin.utils import head_tail_content

        content = "hello world"
        # partial=100 → half=50 → content (11 chars) < 50, so returned verbatim
        assert head_tail_content(content, 100) == content

    def test_long_content_split(self):
        from plugin.utils import head_tail_content

        # partial=10 → half=5; content (20 chars) > half
        # → content[:5] + "\n\n" + content[-5:]
        content = "abcdefghij1234567890"
        result = head_tail_content(content, 10)
        assert result == "abcde\n\n67890"

    def test_partial_zero_returns_empty(self):
        from plugin.utils import head_tail_content

        assert head_tail_content("anything", 0) == ""
        assert head_tail_content("anything", 1) == ""  # half=0

    def test_exact_split(self):
        from plugin.utils import head_tail_content

        # partial=4, half=2; content="abcde" (5 chars > 2)
        # → content[:2] + "\n\n" + content[-2:] = "ab\n\nde"
        assert head_tail_content("abcde", 4) == "ab\n\nde"


# ── list_trimmed_filenames ────────────────────────────────────────────────────


class TestListTrimmedFilenames:
    def test_multiple_extensions(self):
        from plugin.utils import list_trimmed_filenames

        result = list(list_trimmed_filenames("file.bak.tmp"))
        assert result == ["file.bak.tmp", "file.bak", "file"]

    def test_skip_self(self):
        from plugin.utils import list_trimmed_filenames

        result = list(list_trimmed_filenames("file.bak.tmp", skip_self=True))
        assert result == ["file.bak", "file"]

    def test_no_extension(self):
        from plugin.utils import list_trimmed_filenames

        result = list(list_trimmed_filenames("Makefile"))
        assert result == ["Makefile"]

    def test_single_extension(self):
        from plugin.utils import list_trimmed_filenames

        result = list(list_trimmed_filenames("script.py"))
        assert result == ["script.py", "script"]


# ── str_finditer ──────────────────────────────────────────────────────────────


class TestStrFinditer:
    def test_single_occurrence(self):
        from plugin.utils import str_finditer

        result = list(str_finditer("hello world", "world"))
        assert result == [6]

    def test_multiple_occurrences(self):
        from plugin.utils import str_finditer

        result = list(str_finditer("ababab", "ab"))
        assert result == [0, 2, 4]

    def test_no_match(self):
        from plugin.utils import str_finditer

        result = list(str_finditer("hello", "xyz"))
        assert result == []

    def test_empty_substr_raises(self):
        from plugin.utils import str_finditer

        with pytest.raises(ValueError, match="empty string"):
            list(str_finditer("hello", ""))
