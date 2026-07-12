"""Tests for built-in constraint implementations."""

import pytest

from plugin.rules.constraint import AlwaysFalsyException

# ── ContainsConstraint ────────────────────────────────────────────────────────


class TestContainsConstraint:
    def test_needle_found(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        snap = make_snapshot(content="hello world")
        assert ContainsConstraint("hello").test(snap) is True

    def test_needle_not_found(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        snap = make_snapshot(content="hello world")
        assert ContainsConstraint("python").test(snap) is False

    def test_one_of_multiple_needles_found(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        snap = make_snapshot(content="hello world")
        assert ContainsConstraint("python", "hello").test(snap) is True

    def test_threshold_met(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        # "ab" appears 3 times
        snap = make_snapshot(content="ab ab ab")
        assert ContainsConstraint("ab", threshold=3).test(snap) is True

    def test_threshold_not_met(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        snap = make_snapshot(content="ab ab")
        assert ContainsConstraint("ab", threshold=3).test(snap) is False

    def test_threshold_zero_always_true(self, make_snapshot):
        from plugin.rules.constraints.contains import ContainsConstraint

        snap = make_snapshot(content="")
        assert ContainsConstraint("anything", threshold=0).test(snap) is True

    def test_no_needles_is_droppable(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint().is_droppable() is True

    def test_with_needles_not_droppable(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint("foo").is_droppable() is False


# ── ContainsRegexConstraint ───────────────────────────────────────────────────


class TestContainsRegexConstraint:
    def test_regex_matches(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="version: 1.2.3")
        assert ContainsRegexConstraint(r"\d+\.\d+").test(snap) is True

    def test_regex_no_match(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="hello world")
        assert ContainsRegexConstraint(r"\d+").test(snap) is False

    def test_threshold_met(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="cat dog cat dog cat")
        assert ContainsRegexConstraint(r"cat", threshold=3).test(snap) is True

    def test_threshold_not_met(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="cat dog cat")
        assert ContainsRegexConstraint(r"cat", threshold=3).test(snap) is False

    def test_threshold_zero_always_true(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="")
        assert ContainsRegexConstraint(r"anything", threshold=0).test(snap) is True

    def test_multiple_patterns_as_alternation(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="bar")
        # Two patterns merged into one alternation
        assert ContainsRegexConstraint("foo", "bar").test(snap) is True


# ── FirstLineContainsConstraint ───────────────────────────────────────────────


class TestFirstLineContainsConstraint:
    def test_found_in_first_line(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains import FirstLineContainsConstraint

        snap = make_snapshot(first_line="#!/usr/bin/env python")
        assert FirstLineContainsConstraint("python").test(snap) is True

    def test_not_in_first_line(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains import FirstLineContainsConstraint

        snap = make_snapshot(first_line="#!/usr/bin/bash")
        assert FirstLineContainsConstraint("python").test(snap) is False

    def test_one_of_multiple_needles(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains import FirstLineContainsConstraint

        snap = make_snapshot(first_line="#!/usr/bin/ruby")
        assert FirstLineContainsConstraint("python", "ruby").test(snap) is True

    def test_no_needles_is_droppable(self):
        from plugin.rules.constraints.first_line_contains import FirstLineContainsConstraint

        assert FirstLineContainsConstraint().is_droppable() is True


# ── FirstLineContainsRegexConstraint ─────────────────────────────────────────


class TestFirstLineContainsRegexConstraint:
    def test_regex_matches_first_line(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        snap = make_snapshot(first_line="#!/usr/bin/python3")
        assert FirstLineContainsRegexConstraint(r"python\d?").test(snap) is True

    def test_regex_no_match(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        snap = make_snapshot(first_line="#!/bin/bash")
        assert FirstLineContainsRegexConstraint(r"python").test(snap) is False

    def test_case_insensitive_flag(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        snap = make_snapshot(first_line="# -*- coding: UTF-8 -*-")
        assert FirstLineContainsRegexConstraint(r"utf-8", regex_flags=["IGNORECASE"]).test(snap) is True


# ── IsInterpreterConstraint ───────────────────────────────────────────────────


class TestIsInterpreterConstraint:
    def test_shebang_exact(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="#!/usr/bin/python")
        assert IsInterpreterConstraint("python").test(snap) is True

    def test_shebang_env(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="#!/usr/bin/env python")
        assert IsInterpreterConstraint("python").test(snap) is True

    def test_shebang_wrong_interpreter(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="#!/usr/bin/bash")
        assert IsInterpreterConstraint("python").test(snap) is False

    def test_vim_modeline(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="# vim: syntax=python")
        assert IsInterpreterConstraint("python").test(snap) is True

    def test_vim_modeline_with_trailing_options(self, make_snapshot):
        """A real VIM modeline usually continues with more options after `syntax=`, e.g.
        `syntax=python ts=4`, not just `syntax=python` at the very end of the line."""
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="# vim: syntax=python ts=4:")
        assert IsInterpreterConstraint("python").test(snap) is True

    def test_loosy_version_matches_numbered(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="#!/usr/bin/python3.11")
        assert IsInterpreterConstraint("python", loosy_version=True).test(snap) is True

    def test_loosy_version_strict_fails(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        # Without loosy_version, "python3" won't match the "python" boundary
        snap = make_snapshot(first_line="#!/usr/bin/python3")
        assert IsInterpreterConstraint("python").test(snap) is False

    def test_no_shebang(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="print('hello')")
        assert IsInterpreterConstraint("python").test(snap) is False

    def test_empty_first_line(self, make_snapshot):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        snap = make_snapshot(first_line="")
        assert IsInterpreterConstraint("python").test(snap) is False


# ── IsNameConstraint ──────────────────────────────────────────────────────────


class TestIsNameConstraint:
    def test_exact_match(self, make_snapshot):
        from plugin.rules.constraints.is_name import IsNameConstraint

        snap = make_snapshot(path="/home/user/Makefile")
        assert IsNameConstraint("Makefile", case_insensitive=False).test(snap) is True

    def test_no_match(self, make_snapshot):
        from plugin.rules.constraints.is_name import IsNameConstraint

        snap = make_snapshot(path="/home/user/Dockerfile")
        assert IsNameConstraint("Makefile", case_insensitive=False).test(snap) is False

    def test_case_insensitive(self, make_snapshot):
        from plugin.rules.constraints.is_name import IsNameConstraint

        snap = make_snapshot(path="/home/user/makefile")
        assert IsNameConstraint("Makefile", case_insensitive=True).test(snap) is True

    def test_one_of_multiple_names(self, make_snapshot):
        from plugin.rules.constraints.is_name import IsNameConstraint

        snap = make_snapshot(path="/home/user/Dockerfile")
        assert IsNameConstraint("Makefile", "Dockerfile", case_insensitive=False).test(snap) is True

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraints.is_name import IsNameConstraint

        snap = make_snapshot()  # path=None
        with pytest.raises(AlwaysFalsyException):
            IsNameConstraint("Makefile").test(snap)

    def test_no_names_is_droppable(self):
        from plugin.rules.constraints.is_name import IsNameConstraint

        assert IsNameConstraint().is_droppable() is True


# ── NameContainsConstraint ────────────────────────────────────────────────────


class TestNameContainsConstraint:
    def test_needle_in_name(self, make_snapshot):
        from plugin.rules.constraints.name_contains import NameContainsConstraint

        snap = make_snapshot(path="/home/user/my_script.py")
        assert NameContainsConstraint("script").test(snap) is True

    def test_needle_not_in_name(self, make_snapshot):
        from plugin.rules.constraints.name_contains import NameContainsConstraint

        snap = make_snapshot(path="/home/user/main.py")
        assert NameContainsConstraint("script").test(snap) is False

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraints.name_contains import NameContainsConstraint

        snap = make_snapshot()
        with pytest.raises(AlwaysFalsyException):
            NameContainsConstraint("anything").test(snap)


# ── PathContainsConstraint ────────────────────────────────────────────────────


class TestPathContainsConstraint:
    def test_needle_in_path(self, make_snapshot):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        snap = make_snapshot(path="/home/user/projects/myapp/main.py")
        assert PathContainsConstraint("projects").test(snap) is True

    def test_needle_not_in_path(self, make_snapshot):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        snap = make_snapshot(path="/home/user/main.py")
        assert PathContainsConstraint("projects").test(snap) is False

    def test_multiple_needles_one_matches(self, make_snapshot):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        snap = make_snapshot(path="/home/user/src/main.py")
        assert PathContainsConstraint("projects", "src").test(snap) is True

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        snap = make_snapshot()
        with pytest.raises(AlwaysFalsyException):
            PathContainsConstraint("anything").test(snap)

    def test_no_needles_is_droppable(self):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        assert PathContainsConstraint().is_droppable() is True


# ── IsLineCountConstraint ─────────────────────────────────────────────────────


class TestIsLineCountConstraint:
    def test_greater_than_true(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=10)
        assert IsLineCountConstraint(">", 5).test(snap) is True

    def test_greater_than_false(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=3)
        assert IsLineCountConstraint(">", 5).test(snap) is False

    def test_equal(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=5)
        assert IsLineCountConstraint("==", 5).test(snap) is True

    def test_not_equal(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=5)
        assert IsLineCountConstraint("!=", 5).test(snap) is False

    def test_less_than(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=2)
        assert IsLineCountConstraint("<", 5).test(snap) is True

    def test_wrong_arg_count_is_droppable(self):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        assert IsLineCountConstraint(">").is_droppable() is True
        assert IsLineCountConstraint().is_droppable() is True

    def test_valid_not_droppable(self):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        assert IsLineCountConstraint(">", 10).is_droppable() is False

    def test_gte_alias(self, make_snapshot):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        snap = make_snapshot(line_count=5)
        assert IsLineCountConstraint("gte", 5).test(snap) is True


# ── IsSizeConstraint ──────────────────────────────────────────────────────────


class TestIsSizeConstraint:
    def test_file_on_disk_larger(self, make_snapshot):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        snap = make_snapshot(file_size=2048)
        assert IsSizeConstraint(">", 1000).test(snap) is True

    def test_file_on_disk_smaller(self, make_snapshot):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        snap = make_snapshot(file_size=500)
        assert IsSizeConstraint(">", 1000).test(snap) is False

    def test_file_not_on_disk_raises(self, make_snapshot):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        snap = make_snapshot(file_size=-1)
        with pytest.raises(AlwaysFalsyException):
            IsSizeConstraint(">", 1000).test(snap)

    def test_equal(self, make_snapshot):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        snap = make_snapshot(file_size=1024)
        assert IsSizeConstraint("==", 1024).test(snap) is True

    def test_wrong_arg_count_is_droppable(self):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        assert IsSizeConstraint(">").is_droppable() is True
        assert IsSizeConstraint().is_droppable() is True

    def test_valid_not_droppable(self):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        assert IsSizeConstraint(">", 0).is_droppable() is False


# ── IsPlatformConstraint ──────────────────────────────────────────────────────


class TestIsPlatformConstraint:
    # The sublime mock returns platform() == "linux"

    def test_matching_platform(self, make_snapshot):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        snap = make_snapshot()
        assert IsPlatformConstraint("linux").test(snap) is True

    def test_non_matching_platform(self, make_snapshot):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        snap = make_snapshot()
        assert IsPlatformConstraint("windows").test(snap) is False

    def test_case_insensitive_matching(self, make_snapshot):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        snap = make_snapshot()
        assert IsPlatformConstraint("Linux").test(snap) is True

    def test_one_of_multiple_platforms(self, make_snapshot):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        snap = make_snapshot()
        assert IsPlatformConstraint("windows", "linux").test(snap) is True

    def test_empty_args_is_droppable(self):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        assert IsPlatformConstraint().is_droppable() is True


# ── AbstractConstraint class methods ──────────────────────────────────────────


class TestAbstractConstraintClassMethods:
    def test_name_derives_from_class_name(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint.name() == "contains"

    def test_name_multi_word(self):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        assert IsLineCountConstraint.name() == "is_line_count"

    def test_can_support_matching_string(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint.can_support("contains") is True

    def test_can_support_non_matching_string(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint.can_support("contains_regex") is False


# ── IsArchConstraint ────────────────────────────────────────────────────────


class TestIsArchConstraint:
    def test_matching_arch(self, make_snapshot):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        snap = make_snapshot()
        # ST_ARCH is resolved at import time; in the test mock it's "x64"
        assert IsArchConstraint("x64").test(snap) is True

    def test_non_matching_arch(self, make_snapshot):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        snap = make_snapshot()
        assert IsArchConstraint("x32").test(snap) is False

    def test_one_of_multiple(self, make_snapshot):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        snap = make_snapshot()
        assert IsArchConstraint("x32", "x64").test(snap) is True

    def test_case_insensitive(self, make_snapshot):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        snap = make_snapshot()
        assert IsArchConstraint("X64").test(snap) is True

    def test_empty_is_droppable(self):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        assert IsArchConstraint().is_droppable() is True

    def test_name(self):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        assert IsArchConstraint.name() == "is_arch"


# ── IsPlatformArchConstraint ────────────────────────────────────────────────


class TestIsPlatformArchConstraint:
    def test_matching_platform_arch(self, make_snapshot):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        snap = make_snapshot()
        # ST_PLATFORM_ARCH is resolved at import time; mock returns "linux_x64"
        assert IsPlatformArchConstraint("linux_x64").test(snap) is True

    def test_non_matching(self, make_snapshot):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        snap = make_snapshot()
        assert IsPlatformArchConstraint("windows_x64").test(snap) is False

    def test_empty_is_droppable(self):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        assert IsPlatformArchConstraint().is_droppable() is True

    def test_name(self):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        assert IsPlatformArchConstraint.name() == "is_platform_arch"


# ── IsHiddenSyntaxConstraint ────────────────────────────────────────────────


class TestIsHiddenSyntaxConstraint:
    def test_hidden_syntax(self, make_snapshot):
        from unittest.mock import MagicMock

        from plugin.rules.constraints.is_hidden_syntax import IsHiddenSyntaxConstraint

        snap = make_snapshot()
        # Inject a mock syntax with hidden=True
        mock_syntax = MagicMock()
        mock_syntax.hidden = True
        object.__setattr__(snap, "syntax", mock_syntax)

        assert IsHiddenSyntaxConstraint().test(snap) is True

    def test_visible_syntax(self, make_snapshot):
        from unittest.mock import MagicMock

        from plugin.rules.constraints.is_hidden_syntax import IsHiddenSyntaxConstraint

        snap = make_snapshot()
        mock_syntax = MagicMock()
        mock_syntax.hidden = False
        object.__setattr__(snap, "syntax", mock_syntax)

        assert IsHiddenSyntaxConstraint().test(snap) is False

    def test_no_syntax_raises(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_hidden_syntax import IsHiddenSyntaxConstraint

        snap = make_snapshot()  # syntax=None
        with pytest.raises(AlwaysFalsyException):
            IsHiddenSyntaxConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_hidden_syntax import IsHiddenSyntaxConstraint

        assert IsHiddenSyntaxConstraint.name() == "is_hidden_syntax"


# ── SelectorMatchesConstraint ───────────────────────────────────────────────


class TestSelectorMatchesConstraint:
    def test_no_candidates_is_droppable(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint().is_droppable() is True

    def test_with_candidates_not_droppable(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint("source.python").is_droppable() is False

    def test_no_syntax_raises(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        snap = make_snapshot()  # syntax=None
        with pytest.raises(AlwaysFalsyException):
            SelectorMatchesConstraint("source.python").test(snap)

    def test_name(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint.name() == "selector_matches"
