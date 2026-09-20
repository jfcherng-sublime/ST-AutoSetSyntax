"""Tests for built-in constraint implementations."""

import pytest

from plugin.rules.constraint import AlwaysFalsyException
from plugin.types import Fold

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

    def test_no_needles_folds_to_false(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint().fold().value is False

    def test_with_needles_does_not_fold(self):
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint("foo").fold().value is None

    def test_threshold_zero_no_needles_folds_to_true(self):
        """threshold<=0 makes test() a constant True even with no needles (see
        test_threshold_zero_always_true), so it folds to True -- not False, which would
        invert the rule's meaning, and not None, which would keep testing a settled
        answer on every view."""
        from plugin.rules.constraints.contains import ContainsConstraint

        assert ContainsConstraint(threshold=0).fold().value is True


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

    def test_no_patterns_folds_to_false(self):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        assert ContainsRegexConstraint().fold().value is False

    def test_with_patterns_does_not_fold(self):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        assert ContainsRegexConstraint("foo").fold().value is None

    def test_threshold_zero_no_patterns_folds_to_true(self):
        """Same reasoning as ContainsConstraint's equivalent test: threshold<=0 is a constant
        True regardless of patterns."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        assert ContainsRegexConstraint(threshold=0).fold().value is True

    def test_null_regex_flags_falls_back_to_multiline_default(self, make_snapshot):
        """Regression (AbstractConstraint._handled_regex): "regex_flags": null is present with
        value None, not absent, so `kwargs.get("regex_flags", [...])`'s default doesn't cover it
        -- parse_regex_flags(None) raised TypeError. Must fall back to the ["MULTILINE"] default."""
        import re

        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint("foo", regex_flags=None)
        assert constraint.regex.flags & re.MULTILINE
        snap = make_snapshot(content="foo")
        assert constraint.test(snap) is True

    def test_empty_regex_flags_list_disables_multiline_default(self, make_snapshot):
        """An explicit `regex_flags: []` is a distinct, valid "no flags at all, not even
        MULTILINE" setting and must not be coerced into the `["MULTILINE"]` default."""
        import re

        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint("foo", regex_flags=[])
        assert not (constraint.regex.flags & re.MULTILINE)

    def test_empty_pattern_falls_through_to_match_nothing(self, make_snapshot):
        """Regression: `_handled_regex` didn't drop falsy args, so `contains_regex("")`
        compiled `(?:)` (matches at every position, constant True). Now falsy entries are
        dropped like `_handled_args` does, yielding the 'match nothing' sentinel instead."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint("")
        assert constraint.fold().value is False
        snap = make_snapshot(content="anything")
        assert constraint.test(snap) is False

    def test_none_pattern_falls_through_to_match_nothing(self, make_snapshot):
        """Same as above but with a JSON `null` in args, which becomes Python None."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint(None)
        assert constraint.fold().value is False
        snap = make_snapshot(content="anything")
        assert constraint.test(snap) is False

    def test_mixed_valid_and_empty_patterns_use_only_valid(self, make_snapshot):
        """When some patterns are valid and some are falsy, the falsy ones are dropped and
        the valid ones are used. Previously an empty-string-first arg like ("", "foo") caused
        the whole merged regex to become a constant-True sub-pattern."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint("", "foo")
        # has a valid pattern "foo", so NOT droppable
        assert constraint.fold().value is None
        snap = make_snapshot(content="foo")
        assert constraint.test(snap) is True
        snap = make_snapshot(content="bar")
        assert constraint.test(snap) is False


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

    def test_no_needles_folds_to_false(self):
        from plugin.rules.constraints.first_line_contains import FirstLineContainsConstraint

        assert FirstLineContainsConstraint().fold().value is False


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

    def test_no_patterns_folds_to_false(self):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        assert FirstLineContainsRegexConstraint().fold().value is False

    def test_with_patterns_does_not_fold(self):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        assert FirstLineContainsRegexConstraint("python").fold().value is None

    def test_empty_pattern_folds_to_false(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        assert FirstLineContainsRegexConstraint("").fold().value is False
        snap = make_snapshot(first_line="anything")
        assert FirstLineContainsRegexConstraint("").test(snap) is False


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

    def test_no_interpreters_folds_to_false(self):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        assert IsInterpreterConstraint().fold().value is False

    def test_with_interpreter_does_not_fold(self):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        assert IsInterpreterConstraint("python").fold().value is None


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

    def test_no_names_folds_to_false(self):
        from plugin.rules.constraints.is_name import IsNameConstraint

        assert IsNameConstraint().fold().value is False


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

    def test_no_needles_folds_to_false(self):
        from plugin.rules.constraints.name_contains import NameContainsConstraint

        assert NameContainsConstraint().fold().value is False


# ── NameContainsRegexConstraint ───────────────────────────────────────────────


class TestNameContainsRegexConstraint:
    def test_regex_matches_name(self, make_snapshot):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        snap = make_snapshot(path="/home/user/my_script.py")
        assert NameContainsRegexConstraint(r"script").test(snap) is True

    def test_regex_no_match(self, make_snapshot):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        snap = make_snapshot(path="/home/user/main.py")
        assert NameContainsRegexConstraint(r"script").test(snap) is False

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        snap = make_snapshot()
        with pytest.raises(AlwaysFalsyException):
            NameContainsRegexConstraint("anything").test(snap)

    def test_no_patterns_folds_to_false(self):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        assert NameContainsRegexConstraint().fold().value is False

    def test_with_patterns_does_not_fold(self):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        assert NameContainsRegexConstraint("script").fold().value is None

    def test_empty_pattern_folds_to_false(self, make_snapshot):
        from plugin.rules.constraints.name_contains_regex import NameContainsRegexConstraint

        assert NameContainsRegexConstraint("").fold().value is False
        snap = make_snapshot(path="file.py")
        assert NameContainsRegexConstraint("").test(snap) is False


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

    def test_no_needles_folds_to_false(self):
        from plugin.rules.constraints.path_contains import PathContainsConstraint

        assert PathContainsConstraint().fold().value is False


# ── PathContainsRegexConstraint ───────────────────────────────────────────────


class TestPathContainsRegexConstraint:
    def test_regex_matches_path(self, make_snapshot):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        snap = make_snapshot(path="/home/user/projects/myapp/main.py")
        assert PathContainsRegexConstraint(r"projects").test(snap) is True

    def test_regex_no_match(self, make_snapshot):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        snap = make_snapshot(path="/home/user/main.py")
        assert PathContainsRegexConstraint(r"projects").test(snap) is False

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        snap = make_snapshot()
        with pytest.raises(AlwaysFalsyException):
            PathContainsRegexConstraint("anything").test(snap)

    def test_no_patterns_folds_to_false(self):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        assert PathContainsRegexConstraint().fold().value is False

    def test_with_patterns_does_not_fold(self):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        assert PathContainsRegexConstraint("projects").fold().value is None

    def test_empty_pattern_folds_to_false(self, make_snapshot):
        from plugin.rules.constraints.path_contains_regex import PathContainsRegexConstraint

        assert PathContainsRegexConstraint("").fold().value is False
        snap = make_snapshot(path="/home/file.py")
        assert PathContainsRegexConstraint("").test(snap) is False


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

    def test_wrong_arg_count_folds_to_false(self):
        """Assert the whole `Fold`: both failure branches fold to the same `False`, so the
        reason is the only thing that tells them apart."""
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        expected = "expects exactly 2 args (a comparator and a threshold), got {}"
        assert IsLineCountConstraint(">").fold() == Fold(False, expected.format(1))
        assert IsLineCountConstraint().fold() == Fold(False, expected.format(0))

    def test_unknown_comparator_folds_to_false(self):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        assert IsLineCountConstraint("~~", 10).fold() == Fold(False, "'~~' is not a known comparator")

    def test_valid_does_not_fold(self):
        from plugin.rules.constraints.is_line_count import IsLineCountConstraint

        assert IsLineCountConstraint(">", 10).fold().value is None

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

    def test_wrong_arg_count_folds_to_false(self):
        """See IsLineCountConstraint's twin: the reason is what distinguishes the branches."""
        from plugin.rules.constraints.is_size import IsSizeConstraint

        expected = "expects exactly 2 args (a comparator and a threshold), got {}"
        assert IsSizeConstraint(">").fold() == Fold(False, expected.format(1))
        assert IsSizeConstraint().fold() == Fold(False, expected.format(0))

    def test_unknown_comparator_folds_to_false(self):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        assert IsSizeConstraint("~~", 0).fold() == Fold(False, "'~~' is not a known comparator")

    def test_valid_does_not_fold(self):
        from plugin.rules.constraints.is_size import IsSizeConstraint

        assert IsSizeConstraint(">", 0).fold().value is None


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

    def test_empty_args_folds_to_false(self):
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        assert IsPlatformConstraint().fold() == Fold(False, "no platform was given")

    def test_guaranteed_false_folds_to_false(self):
        """The platform is fixed at install time, so a constraint that can never match given the
        current platform is just as much a compile-time constant as one with no names at all --
        the optimizer should be able to prune it the same way."""
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        assert IsPlatformConstraint("windows").fold() == Fold(False, 'this Sublime Text is linux, not any of "windows"')

    def test_guaranteed_true_does_not_fold(self):
        """`fold()` could report `True` here -- the platform is fixed at install time, so this
        constraint is a constant on this machine. It deliberately doesn't: unlike a degenerate
        config (`contains(threshold=0)`), a platform check that matches is a normal, intended
        rule, and folding it would report it to the user as a dropped rule on exactly the
        platform it was written for."""
        from plugin.rules.constraints.is_platform import IsPlatformConstraint

        assert IsPlatformConstraint("linux").fold().value is None


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

    def test_empty_folds_to_false(self):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        assert IsArchConstraint().fold() == Fold(False, "no architecture was given")

    def test_guaranteed_false_folds_to_false(self):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        assert IsArchConstraint("x32").fold() == Fold(False, 'this Sublime Text is x64, not any of "x32"')

    def test_guaranteed_true_does_not_fold(self):
        from plugin.rules.constraints.is_arch import IsArchConstraint

        assert IsArchConstraint("x64").fold().value is None

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

    def test_empty_folds_to_false(self):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        assert IsPlatformArchConstraint().fold() == Fold(False, "no platform/arch pair was given")

    def test_guaranteed_false_folds_to_false(self):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        assert IsPlatformArchConstraint("windows_x64").fold() == Fold(
            False, 'this Sublime Text is linux_x64, not any of "windows_x64"'
        )

    def test_guaranteed_true_does_not_fold(self):
        from plugin.rules.constraints.is_platform_arch import IsPlatformArchConstraint

        assert IsPlatformArchConstraint("linux_x64").fold().value is None

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
    def test_no_candidates_folds_to_false(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint().fold().value is False

    def test_with_candidates_does_not_fold(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint("source.python").fold().value is None

    def test_no_syntax_raises(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        snap = make_snapshot()  # syntax=None
        with pytest.raises(AlwaysFalsyException):
            SelectorMatchesConstraint("source.python").test(snap)

    def test_name(self):
        from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

        assert SelectorMatchesConstraint.name() == "selector_matches"
