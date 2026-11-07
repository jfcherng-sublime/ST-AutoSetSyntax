"""Tests for built-in constraint implementations."""

import importlib
import re
from unittest.mock import MagicMock

import pytest

from plugin.rules.constraint import ConstraintRule
from plugin.types import Fold


def _cls(path: str) -> type:
    module, cls_name = path.split(".")
    return getattr(importlib.import_module(f"plugin.rules.constraints.{module}"), cls_name)


# ── Text constraints: contains / first_line_contains / name_contains / path_contains (+ _regex) ──

# (class, snapshot kwargs, a needle found in them, a needle not found in them)
_PLAIN_CASES = [
    ("contains.ContainsConstraint", {"content": "hello world"}, "hello", "python"),
    ("first_line_contains.FirstLineContainsConstraint", {"first_line": "#!/usr/bin/env python"}, "python", "ruby"),
    ("name_contains.NameContainsConstraint", {"path": "/home/user/my_script.py"}, "script", "main"),
    ("path_contains.PathContainsConstraint", {"path": "/home/user/projects/main.py"}, "projects", "nothing"),
]
_REGEX_CASES = [
    ("contains_regex.ContainsRegexConstraint", {"content": "version: 1.2.3"}, r"\d+\.\d+", r"[a-z]{20}"),
    (
        "first_line_contains_regex.FirstLineContainsRegexConstraint",
        {"first_line": "#!/usr/bin/python3"},
        r"python\d?",
        "ruby",
    ),
    ("name_contains_regex.NameContainsRegexConstraint", {"path": "/home/user/my_script.py"}, "script", "^main"),
    (
        "path_contains_regex.PathContainsRegexConstraint",
        {"path": "/home/user/projects/main.py"},
        "projects",
        "^nothing",
    ),
]
_TEXT_CASES = _PLAIN_CASES + _REGEX_CASES


@pytest.mark.parametrize(("cls_path", "snap_kwargs", "hit", "miss"), _TEXT_CASES)
class TestTextConstraints:
    def test_needle_found_or_not(self, make_snapshot, cls_path, snap_kwargs, hit, miss):
        snap = make_snapshot(**snap_kwargs)
        assert _cls(cls_path)(hit).test(snap) is True
        assert _cls(cls_path)(miss).test(snap) is False

    def test_any_of_several_needles_is_enough(self, make_snapshot, cls_path, snap_kwargs, hit, miss):
        assert _cls(cls_path)(miss, hit).test(make_snapshot(**snap_kwargs)) is True

    def test_no_needles_can_never_match_so_folds_to_false(self, cls_path, snap_kwargs, hit, miss):
        assert _cls(cls_path)().fold().value is False

    def test_with_needles_depends_on_the_view(self, cls_path, snap_kwargs, hit, miss):
        assert _cls(cls_path)(hit).fold().value is None


@pytest.mark.parametrize(
    "cls_path",
    [
        "name_contains.NameContainsConstraint",
        "name_contains_regex.NameContainsRegexConstraint",
        "path_contains.PathContainsConstraint",
        "path_contains_regex.PathContainsRegexConstraint",
        "is_name.IsNameConstraint",
        "is_size.IsSizeConstraint",
        "is_hidden_syntax.IsHiddenSyntaxConstraint",
        "selector_matches.SelectorMatchesConstraint",
    ],
)
def test_constraint_about_a_missing_file_or_syntax_never_passes_even_inverted(make_snapshot, cls_path):
    """With no file (or no syntax) there is nothing to be about, so "inverted" must not turn that into a match."""
    args = {"is_size": (">", 1000), "is_hidden_syntax": ()}.get(cls_path.split(".")[0], ("anything",))
    snap = make_snapshot(file_size=-1)  # no path, no syntax
    for inverted in (False, True):
        assert ConstraintRule(constraint=_cls(cls_path)(*args), inverted=inverted).test(snap) is False


@pytest.mark.parametrize(("cls_path", "snap_kwargs", "hit", "miss"), _REGEX_CASES)
def test_empty_or_null_regex_pattern_matches_nothing(make_snapshot, cls_path, snap_kwargs, hit, miss):
    """Regression: falsy patterns used to compile to `(?:)`, which matches everywhere (constant True)."""
    snap = make_snapshot(**snap_kwargs)
    for pattern in ("", None):
        constraint = _cls(cls_path)(pattern)
        assert constraint.fold().value is False
        assert constraint.test(snap) is False


# ── ContainsConstraint / ContainsRegexConstraint: threshold ──────────────────


@pytest.mark.parametrize(
    ("cls_path", "needle"),
    [("contains.ContainsConstraint", "ab"), ("contains_regex.ContainsRegexConstraint", "ab")],
)
class TestContainsThreshold:
    @pytest.mark.parametrize(("count", "expected"), [(3, True), (2, False)])
    def test_needs_at_least_threshold_occurrences(self, make_snapshot, cls_path, needle, count, expected):
        snap = make_snapshot(content=" ".join([needle] * count))
        assert _cls(cls_path)(needle, threshold=3).test(snap) is expected

    def test_threshold_zero_always_matches_even_without_needles(self, make_snapshot, cls_path, needle):
        """threshold<=0 makes test() a constant True, so it folds to True -- not False, which would
        invert the rule's meaning, and not None, which would keep testing a settled answer."""
        assert _cls(cls_path)(needle, threshold=0).test(make_snapshot(content="")) is True
        assert _cls(cls_path)(threshold=0).fold().value is True

    @pytest.mark.parametrize("threshold", ["2", 1.5, True, None])
    def test_non_integer_threshold_raises(self, cls_path, needle, threshold):
        """Raise rather than fold to False: under "not", False would flip to "always matches"."""
        with pytest.raises(ValueError, match='"threshold" must be an integer'):
            _cls(cls_path)(needle, threshold=threshold)


# ── ContainsRegexConstraint: flags and pattern merging ───────────────────────


class TestContainsRegexConstraint:
    def test_multiple_patterns_are_alternatives(self, make_snapshot):
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        assert ContainsRegexConstraint("foo", "bar").test(make_snapshot(content="bar")) is True

    def test_multiline_is_the_default_and_null_flags_fall_back_to_it(self, make_snapshot):
        """Regression: "regex_flags": null is present with value None, not absent, so the default
        didn't cover it and parsing raised TypeError."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        snap = make_snapshot(content="x\nfoo")
        assert ContainsRegexConstraint("^foo").test(snap) is True
        assert ContainsRegexConstraint("^foo", regex_flags=None).test(snap) is True

    def test_empty_regex_flags_list_disables_the_multiline_default(self, make_snapshot):
        """`regex_flags: []` is a valid "no flags at all" and must not be coerced into the default."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        assert ContainsRegexConstraint("^foo", regex_flags=[]).test(make_snapshot(content="x\nfoo")) is False

    def test_falsy_patterns_are_dropped_and_the_rest_used(self, make_snapshot):
        """Previously an empty-string-first arg like ("", "foo") made the whole merged regex constant-True."""
        from plugin.rules.constraints.contains_regex import ContainsRegexConstraint

        constraint = ContainsRegexConstraint("", "foo")
        assert constraint.fold().value is None
        assert constraint.test(make_snapshot(content="foo")) is True
        assert constraint.test(make_snapshot(content="bar")) is False

    def test_case_insensitive_flag(self, make_snapshot):
        from plugin.rules.constraints.first_line_contains_regex import FirstLineContainsRegexConstraint

        snap = make_snapshot(first_line="# -*- coding: UTF-8 -*-")
        assert FirstLineContainsRegexConstraint("utf-8", regex_flags=["IGNORECASE"]).test(snap) is True


# ── IsInterpreterConstraint ───────────────────────────────────────────────────


class TestIsInterpreterConstraint:
    @pytest.mark.parametrize(
        ("first_line", "kwargs", "expected"),
        [
            ("#!/usr/bin/python", {}, True),
            ("#!/usr/bin/env python", {}, True),
            ("#!/usr/bin/bash", {}, False),
            ("# vim: syntax=python", {}, True),
            # a real VIM modeline usually continues with more options after `syntax=`
            ("# vim: syntax=python ts=4:", {}, True),
            ("#!/usr/bin/python3.11", {"loosy_version": True}, True),
            ("#!/usr/bin/python3", {}, False),  # "python3" doesn't match the "python" boundary
            ("print('hello')", {}, False),
            ("", {}, False),
        ],
    )
    def test_interpreter_detection(self, make_snapshot, first_line, kwargs, expected):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        assert IsInterpreterConstraint("python", **kwargs).test(make_snapshot(first_line=first_line)) is expected

    def test_fold(self):
        from plugin.rules.constraints.is_interpreter import IsInterpreterConstraint

        assert IsInterpreterConstraint().fold().value is False
        assert IsInterpreterConstraint("python").fold().value is None


# ── IsNameConstraint ──────────────────────────────────────────────────────────


class TestIsNameConstraint:
    @pytest.mark.parametrize(
        ("path", "names", "case_insensitive", "expected"),
        [
            ("/home/user/Makefile", ("Makefile",), False, True),
            ("/home/user/Dockerfile", ("Makefile",), False, False),
            ("/home/user/makefile", ("Makefile",), True, True),
            ("/home/user/Dockerfile", ("Makefile", "Dockerfile"), False, True),
        ],
    )
    def test_name_matching(self, make_snapshot, path, names, case_insensitive, expected):
        from plugin.rules.constraints.is_name import IsNameConstraint

        constraint = IsNameConstraint(*names, case_insensitive=case_insensitive)
        assert constraint.test(make_snapshot(path=path)) is expected

    def test_no_names_folds_to_false(self):
        from plugin.rules.constraints.is_name import IsNameConstraint

        assert IsNameConstraint().fold().value is False


# ── name_contains / path_contains: case sensitivity ───────────────────────────

_CONTAINS_CASES = [
    # (class, file path, needle differing from it only in case, the same needle in the path's case)
    ("name_contains.NameContainsConstraint", "/home/user/Makefile", "makefile", "Makefile"),
    ("path_contains.PathContainsConstraint", "/home/user/Templates/page.html", "/templates/", "/Templates/"),
]


class TestNameAndPathContainsCaseSensitivity:
    """Like `is_name`/`is_extension`: these look at file names, so they follow the filesystem's
    case sensitivity by default -- insensitive on Windows/macOS, sensitive on Linux."""

    @pytest.mark.parametrize(("cls_path", "path", "needle", "exact"), _CONTAINS_CASES)
    def test_explicit_case_insensitive(self, make_snapshot, cls_path, path, needle, exact):
        snap = make_snapshot(path=path)

        assert _cls(cls_path)(needle, case_insensitive=True).test(snap) is True
        assert _cls(cls_path)(needle, case_insensitive=False).test(snap) is False
        assert _cls(cls_path)(exact, case_insensitive=True).test(snap) is True
        assert _cls(cls_path)(exact, case_insensitive=False).test(snap) is True

    @pytest.mark.parametrize(("cls_path", "path", "needle", "exact"), _CONTAINS_CASES)
    @pytest.mark.parametrize(("platform", "matches"), [("windows", True), ("osx", True), ("linux", False)])
    def test_default_follows_the_platform(
        self, make_snapshot, monkeypatch, cls_path, path, needle, exact, platform, matches
    ):
        import plugin.rules.constraint as constraint_mod

        monkeypatch.setattr(constraint_mod, "ST_PLATFORM", platform)

        assert _cls(cls_path)(needle).test(make_snapshot(path=path)) is matches


# ── IsLineCountConstraint / IsSizeConstraint ──────────────────────────────────

_COUNT_CASES = [
    ("is_line_count.IsLineCountConstraint", "line_count"),
    ("is_size.IsSizeConstraint", "file_size"),
]


@pytest.mark.parametrize(("cls_path", "field"), _COUNT_CASES)
class TestComparatorConstraints:
    @pytest.mark.parametrize(
        ("comparator", "actual", "expected"),
        [(">", 10, True), (">", 3, False), ("==", 5, True), ("!=", 5, False), ("<", 2, True), ("gte", 5, True)],
    )
    def test_comparison_against_threshold_five(self, make_snapshot, cls_path, field, comparator, actual, expected):
        snap = make_snapshot(**{field: actual})
        assert _cls(cls_path)(comparator, 5).test(snap) is expected

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            ((">",), "expects exactly 2 args (a comparator and a threshold), got 1"),
            ((), "expects exactly 2 args (a comparator and a threshold), got 0"),
            (("~~", 10), "'~~' is not a known comparator"),
        ],
    )
    def test_invalid_args_raise(self, cls_path, field, args, message):
        """Raise rather than fold to False: under "not", False would flip to "always matches"."""
        with pytest.raises(ValueError, match=re.escape(message)):
            _cls(cls_path)(*args)

    def test_valid_args_depend_on_the_view(self, cls_path, field):
        assert _cls(cls_path)(">", 10).fold().value is None


# ── IsPlatformConstraint / IsArchConstraint / IsPlatformArchConstraint ───────
# The sublime stub reports linux / x64 / linux_x64.

_ENV_CASES = [
    ("is_platform.IsPlatformConstraint", "linux", "windows", "no platform was given"),
    ("is_arch.IsArchConstraint", "x64", "x32", "no architecture was given"),
    ("is_platform_arch.IsPlatformArchConstraint", "linux_x64", "windows_x64", "no platform/arch pair was given"),
]


@pytest.mark.parametrize(("cls_path", "current", "other", "empty_reason"), _ENV_CASES)
class TestEnvironmentConstraints:
    def test_matches_only_the_current_value(self, make_snapshot, cls_path, current, other, empty_reason):
        snap = make_snapshot()
        assert _cls(cls_path)(current).test(snap) is True
        assert _cls(cls_path)(current.upper()).test(snap) is True
        assert _cls(cls_path)(other).test(snap) is False
        assert _cls(cls_path)(other, current).test(snap) is True

    def test_folds_when_it_can_never_match(self, cls_path, current, other, empty_reason):
        """The environment is fixed at install time, so a constraint that can never match is a
        compile-time constant the optimizer may prune."""
        assert _cls(cls_path)().fold() == Fold(False, empty_reason)
        assert _cls(cls_path)(other).fold() == Fold(False, f'this Sublime Text is {current}, not any of "{other}"')

    def test_does_not_fold_when_it_always_matches(self, cls_path, current, other, empty_reason):
        """It could fold to True, but deliberately doesn't: unlike a degenerate config
        (`contains(threshold=0)`), a check that matches is a normal, intended rule, and folding it
        would report it to the user as dropped on exactly the platform it was written for."""
        assert _cls(cls_path)(current).fold().value is None


# ── IsHiddenSyntaxConstraint ────────────────────────────────────────────────


@pytest.mark.parametrize("hidden", [True, False])
def test_is_hidden_syntax_reports_the_syntaxs_hidden_flag(make_snapshot, hidden):
    from plugin.rules.constraints.is_hidden_syntax import IsHiddenSyntaxConstraint

    snap = make_snapshot()
    object.__setattr__(snap, "syntax", MagicMock(hidden=hidden))

    assert IsHiddenSyntaxConstraint().test(snap) is hidden


# ── SelectorMatchesConstraint ───────────────────────────────────────────────


def test_selector_matches_fold():
    from plugin.rules.constraints.selector_matches import SelectorMatchesConstraint

    assert SelectorMatchesConstraint().fold().value is False
    assert SelectorMatchesConstraint("source.python").fold().value is None


# ── Naming ────────────────────────────────────────────────────────────────────


def test_name_is_derived_from_the_class_name():
    from plugin.rules.constraints.contains import ContainsConstraint
    from plugin.rules.constraints.is_line_count import IsLineCountConstraint

    assert ContainsConstraint.name() == "contains"
    assert IsLineCountConstraint.name() == "is_line_count"
    assert ContainsConstraint.can_support("contains") is True
    assert ContainsConstraint.can_support("contains_regex") is False


# ── IsExtensionConstraint ─────────────────────────────────────────────────────


class TestIsExtensionConstraint:
    @staticmethod
    def _test(make_snapshot, path, *args, **kwargs):
        from plugin.rules.constraints.is_extension import IsExtensionConstraint

        return IsExtensionConstraint(*args, **kwargs).test(make_snapshot(path=path))

    def test_extension_given_with_or_without_the_dot(self, make_snapshot):
        assert self._test(make_snapshot, "/tmp/a.py", "py") is True
        assert self._test(make_snapshot, "/tmp/a.py", ".py") is True

    def test_other_extension_does_not_match(self, make_snapshot):
        assert self._test(make_snapshot, "/tmp/a.js", "py") is False

    def test_multi_dot_extension_matches_the_whole_suffix(self, make_snapshot):
        assert self._test(make_snapshot, "/tmp/a.tar.gz", "tar.gz") is True
        assert self._test(make_snapshot, "/tmp/a.tar.gz", "gz") is True
        assert self._test(make_snapshot, "/tmp/a.gz", "tar.gz") is False

    def test_case_sensitivity_follows_the_kwarg(self, make_snapshot):
        assert self._test(make_snapshot, "/tmp/A.PY", "py", case_insensitive=True) is True
        assert self._test(make_snapshot, "/tmp/A.PY", "py", case_insensitive=False) is False
