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


# ── drop_falsy ──────────────────────────────────────────────────────────────


class TestDropFalsy:
    def test_drops_none(self):
        from plugin.utils import drop_falsy

        assert list(drop_falsy([1, None, 2, None, 3])) == [1, 2, 3]

    def test_drops_empty_string(self):
        from plugin.utils import drop_falsy

        assert list(drop_falsy(["a", "", "b"])) == ["a", "b"]

    def test_drops_false(self):
        from plugin.utils import drop_falsy

        assert list(drop_falsy([True, False, True])) == [True, True]

    def test_drops_zero(self):
        from plugin.utils import drop_falsy

        assert list(drop_falsy([0, 1, 2])) == [1, 2]

    def test_empty_iterable(self):
        from plugin.utils import drop_falsy

        assert list(drop_falsy([])) == []


# ── get_fqcn ────────────────────────────────────────────────────────────────


class TestGetFqcn:
    def test_none(self):
        from plugin.utils import get_fqcn

        assert get_fqcn(None) == "None"

    def test_class_object(self):
        from plugin.utils import get_fqcn

        assert get_fqcn(int) == "builtins.int"

    def test_instance(self):
        from plugin.utils import get_fqcn

        assert get_fqcn("hello") == "builtins.str"

    def test_custom_class(self):
        from plugin.utils import get_fqcn

        class Foo:
            pass

        assert get_fqcn(Foo()) == "test_utils.TestGetFqcn.test_custom_class.<locals>.Foo"

    def test_type_object(self):
        from plugin.utils import get_fqcn

        assert get_fqcn(type) == "builtins.type"


# ── merge_literals_to_regex ─────────────────────────────────────────────────


class TestMergeLiteralsToRegex:
    def test_single_literal(self):
        import re

        from plugin.utils import merge_literals_to_regex

        result = merge_literals_to_regex(["hello"])
        assert re.search(result, "hello")

    def test_multiple_literals(self):
        import re

        from plugin.utils import merge_literals_to_regex

        result = merge_literals_to_regex(["foo", "bar"])
        assert re.search(result, "foo")
        assert re.search(result, "bar")
        assert not re.search(result, "baz")

    def test_escapes_special_chars(self):
        import re

        from plugin.utils import merge_literals_to_regex

        result = merge_literals_to_regex(["foo.bar"])
        assert re.search(result, "foo.bar")
        assert not re.search(result, "fooXbar")

    def test_empty_input(self):
        from plugin.utils import merge_literals_to_regex

        result = merge_literals_to_regex([])
        # Empty list produces a never-match pattern
        assert "match nothing" in result

    def test_wrapped_in_non_capturing_group(self):
        from plugin.utils import merge_literals_to_regex

        result = merge_literals_to_regex(["test"])
        assert result.startswith("(?:")
        assert result.endswith(")")


# ── list_all_subclasses ─────────────────────────────────────────────────────


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
        from plugin.utils import list_all_subclasses

        result = list(list_all_subclasses(_A))
        assert _A in result

    def test_skip_self(self):
        from plugin.utils import list_all_subclasses

        result = list(list_all_subclasses(_A, skip_self=True))
        assert _A not in result

    def test_all_leaves(self):
        from plugin.utils import list_all_subclasses

        result = list(list_all_subclasses(_A, skip_self=True))
        assert _B in result
        assert _C in result
        assert _D in result

    def test_skip_abstract(self):
        from abc import ABC
        from abc import abstractmethod

        from plugin.utils import list_all_subclasses

        class _Abstract(ABC):
            @abstractmethod
            def foo(self): ...

        class _Concrete(_Abstract):
            def foo(self): ...

        result = list(list_all_subclasses(_Abstract, skip_abstract=True))
        assert _Abstract not in result
        assert _Concrete in result

    def test_no_subclasses(self):
        from plugin.utils import list_all_subclasses

        class _Leaf:
            pass

        result = list(list_all_subclasses(_Leaf, skip_self=True))
        assert result == []


# ── build_reversed_trie ─────────────────────────────────────────────────────


class TestBuildReversedTrie:
    def test_find_prefixes(self):
        from plugin.utils import build_reversed_trie

        trie = build_reversed_trie((".bak", ".tmp"))
        assert list(trie.find_prefixes("kab.elif"))
        assert not list(trie.find_prefixes("txt.elif"))

    def test_matches_suffixes(self):
        from plugin.utils import build_reversed_trie

        trie = build_reversed_trie((".gz", ".xz"))
        assert list(trie.find_prefixes("zg.xz"))
        assert list(trie.find_prefixes("zg.gz"))
        assert not list(trie.find_prefixes("ip.z"))

    def test_compound_suffixes(self):
        from plugin.utils import build_reversed_trie

        trie = build_reversed_trie((".min.js", ".bundle.js"))
        assert trie.find_prefixes("sj.nim.")
        assert trie.find_prefixes("sj.eldnub.")


# ── list_trimmed_strings ────────────────────────────────────────────────────


class TestListTrimmedStrings:
    def test_trim_suffixes(self):
        from plugin.utils import list_trimmed_strings

        result = list(list_trimmed_strings("file.bak.tmp", (".bak", ".tmp")))
        assert "file.bak.tmp" in result
        assert "file.bak" in result
        assert "file" in result

    def test_skip_self(self):
        from plugin.utils import list_trimmed_strings

        result = list(list_trimmed_strings("file.bak", (".bak",), skip_self=True))
        assert "file.bak" not in result
        assert "file" in result

    def test_no_suffixes(self):
        from plugin.utils import list_trimmed_strings

        result = list(list_trimmed_strings("file", ()))
        assert result == ["file"]

    def test_compound_suffix_trimming(self):
        from plugin.utils import list_trimmed_strings

        result = list(list_trimmed_strings("file.min.js", (".min.js", ".js")))
        assert "file.min.js" in result
        assert "file.min" in result
        assert "file" in result
