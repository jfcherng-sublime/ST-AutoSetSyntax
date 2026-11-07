"""Tests for constraints that need real filesystem paths (repo detection, relative_exists)."""

import pytest

from plugin.rules.constraint import ConstraintRule
from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint
from plugin.rules.constraints.relative_exists import RelativeExistsConstraint


@pytest.mark.parametrize(
    "constraint",
    [RelativeExistsConstraint("a"), IsJavascriptProjectConstraint()],
    ids=lambda constraint: constraint.name(),
)
def test_never_passes_without_a_file_even_inverted(make_snapshot, constraint):
    snap = make_snapshot()  # no path -> not on disk
    for inverted in (False, True):
        assert ConstraintRule(constraint=constraint, inverted=inverted).test(snap) is False


class TestRelativeExistsConstraint:
    def test_sibling_file_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        # Create a temporary file
        sibling = tmp_path / "Gemfile"
        sibling.write_text("")
        test_file = tmp_path / "main.rb"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert RelativeExistsConstraint("Gemfile").test(snap) is True

    def test_sibling_file_missing(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        test_file = tmp_path / "main.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert RelativeExistsConstraint("nonexistent.py").test(snap) is False

    def test_sibling_directory(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        subdir = tmp_path / "node_modules"
        subdir.mkdir()
        test_file = tmp_path / "app.js"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert RelativeExistsConstraint("node_modules/").test(snap) is True

    def test_all_match_mode(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b.txt").write_text("")
        test_file = tmp_path / "main.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        # "all" mode: all must exist
        assert RelativeExistsConstraint("a.txt", "b.txt", match="all").test(snap) is True
        assert RelativeExistsConstraint("a.txt", "missing.txt", match="all").test(snap) is False

    def test_empty_args_folds_to_false(self):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        assert RelativeExistsConstraint().fold().value is False

    def test_null_match_kwarg_does_not_raise(self, make_snapshot, tmp_path):
        """Regression: `match=None` is present with value None, not absent, so
        `kwargs.get("match", "any")`'s default doesn't cover it -- `None.lower()` raised
        AttributeError. Must fall back to the "any" default instead."""
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        (tmp_path / "a.txt").write_text("")
        test_file = tmp_path / "main.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        constraint = RelativeExistsConstraint("a.txt", "missing.txt", match=None)
        assert constraint.test(snap) is True


class TestIsInGitRepoConstraint:
    def test_dot_git_file_worktree(self, make_snapshot, tmp_path):
        """Git worktrees use a .git FILE, not directory."""
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /some/worktree\n")
        test_file = tmp_path / "code.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInGitRepoConstraint().test(snap) is True


class TestIsJavascriptProjectConstraint:
    def test_package_json_without_tsconfig_matches(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        (tmp_path / "package.json").write_text("")
        test_file = tmp_path / "src" / "index.js"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsJavascriptProjectConstraint().test(snap) is True

    def test_package_json_with_tsconfig_does_not_match(self, make_snapshot, tmp_path):
        """The exact TypeScript case this constraint exists to exclude: a package.json alone
        isn't enough proof of a JS (non-TS) project, since TS projects have one too."""
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        (tmp_path / "package.json").write_text("")
        (tmp_path / "tsconfig.json").write_text("")
        test_file = tmp_path / "src" / "index.ts"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsJavascriptProjectConstraint().test(snap) is False

    def test_no_package_json_does_not_match(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        test_file = tmp_path / "index.js"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsJavascriptProjectConstraint().test(snap) is False

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        (tmp_path / "package.json").write_text("")
        test_file = tmp_path / "src" / "components" / "App.jsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsJavascriptProjectConstraint().test(snap) is True

    def test_cached_outer_js_root_does_not_override_a_nearer_typescript_root(self, make_snapshot, tmp_path):
        """A monorepo whose root is JS but holds a TS package: the nearest `package.json` decides,
        so the cached outer root must not answer for a file under the nearer TS one."""
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        (tmp_path / "package.json").write_text("")
        root_file = tmp_path / "index.js"
        root_file.write_text("")
        app = tmp_path / "packages" / "app"
        (app / "src").mkdir(parents=True)
        (app / "package.json").write_text("")
        (app / "tsconfig.json").write_text("")
        app_file = app / "src" / "index.js"
        app_file.write_text("")

        assert IsJavascriptProjectConstraint().test(make_snapshot(path=str(root_file))) is True
        assert IsJavascriptProjectConstraint().test(make_snapshot(path=str(app_file))) is False


class TestIsInPythonDjangoProjectConstraintRealTest:
    """The constraint's own `test()` is materially different from (stricter than) the shared
    `find_parent_with_sibling` helper: it requires *both* a `manage.py` in a
    parent directory *and* a sibling subdirectory of that parent containing all three of
    settings.py/urls.py/wsgi.py (the actual Django-root layout), not just `manage.py` alone.
    """

    @staticmethod
    def _make_django_project(tmp_path, *, django_root_name: str = "myproject"):
        (tmp_path / "manage.py").write_text("")
        django_root = tmp_path / django_root_name
        django_root.mkdir()
        (django_root / "settings.py").write_text("")
        (django_root / "urls.py").write_text("")
        (django_root / "wsgi.py").write_text("")
        return django_root

    def test_full_django_layout_matches(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        self._make_django_project(tmp_path)
        app_file = tmp_path / "myapp" / "models.py"
        app_file.parent.mkdir()
        app_file.write_text("")

        snap = make_snapshot(path=str(app_file))
        assert IsInPythonDjangoProjectConstraint().test(snap) is True

    def test_manage_py_without_django_root_subdir_does_not_match(self, make_snapshot, tmp_path):
        """manage.py alone (no subdirectory with settings/urls/wsgi.py) isn't a real Django
        project as far as this constraint is concerned -- unlike the simpler git/hg/svn/rails
        constraints, which only check for one marker file/dir."""
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        (tmp_path / "manage.py").write_text("")
        app_file = tmp_path / "myapp" / "models.py"
        app_file.parent.mkdir()
        app_file.write_text("")

        snap = make_snapshot(path=str(app_file))
        assert IsInPythonDjangoProjectConstraint().test(snap) is False

    def test_partial_django_root_missing_wsgi_does_not_match(self, make_snapshot, tmp_path):
        """All three of settings.py/urls.py/wsgi.py are required -- two out of three isn't
        enough."""
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        (tmp_path / "manage.py").write_text("")
        django_root = tmp_path / "myproject"
        django_root.mkdir()
        (django_root / "settings.py").write_text("")
        (django_root / "urls.py").write_text("")
        # wsgi.py intentionally missing

        app_file = tmp_path / "myapp" / "models.py"
        app_file.parent.mkdir()
        app_file.write_text("")

        snap = make_snapshot(path=str(app_file))
        assert IsInPythonDjangoProjectConstraint().test(snap) is False

    def test_no_manage_py_anywhere_does_not_match(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        app_file = tmp_path / "myapp" / "models.py"
        app_file.parent.mkdir()
        app_file.write_text("")

        snap = make_snapshot(path=str(app_file))
        assert IsInPythonDjangoProjectConstraint().test(snap) is False


@pytest.mark.parametrize(("setting", "expected"), [(True, True), (False, False), (None, False)])
def test_is_magika_enabled_follows_the_setting_and_defaults_to_off(make_snapshot, setting, expected):
    from unittest.mock import patch

    from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

    with patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=setting):
        assert IsMagikaEnabledConstraint().test(make_snapshot()) is expected


# ── parent-marker constraints ────────────────────────────────────────────────


def _marker_constraints():
    from plugin.rules.constraints._parent_marker import AbstractParentMarkerConstraint
    from plugin.utils import list_all_subclasses

    return sorted(list_all_subclasses(AbstractParentMarkerConstraint, skip_abstract=True), key=lambda c: c.name())


@pytest.fixture(params=_marker_constraints(), ids=lambda cls: cls.name())
def marker_constraint(request):
    """A fresh constraint per test, so one test's found-directory cache can't answer for another."""
    cls = request.param
    cls._found_dirs.clear()
    yield cls()
    cls._found_dirs.clear()


def _make_marker(root, marker):
    """Create `marker` under `root`: a directory if it ends with `/`, else a file."""
    path = root / marker
    if marker.endswith("/"):
        path.mkdir(parents=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    if marker == "manage.py":  # Django also wants a package holding settings/urls/wsgi
        for name in ("settings.py", "urls.py", "wsgi.py"):
            (root / "proj" / name).parent.mkdir(exist_ok=True)
            (root / "proj" / name).write_text("")


def _make_source_file(root):
    source = root / "src" / "app" / "main.txt"
    source.parent.mkdir(parents=True)
    source.write_text("")
    return source


class TestParentMarkerConstraints:
    def test_passes_below_a_directory_holding_the_marker(self, marker_constraint, make_snapshot, tmp_path):
        _make_marker(tmp_path, marker_constraint.marker)
        source = _make_source_file(tmp_path)

        assert marker_constraint.test(make_snapshot(path=str(source))) is True

    def test_fails_without_the_marker(self, marker_constraint, make_snapshot, tmp_path):
        source = _make_source_file(tmp_path)

        assert marker_constraint.test(make_snapshot(path=str(source))) is False

    def test_never_passes_without_a_file(self, marker_constraint, make_snapshot):
        snap = make_snapshot()
        for inverted in (False, True):
            rule = ConstraintRule(constraint=marker_constraint, inverted=inverted)
            assert rule.test(snap) is False

    def test_remembers_the_directory_that_held_the_marker(self, marker_constraint, make_snapshot, tmp_path):
        _make_marker(tmp_path, marker_constraint.marker)
        source = _make_source_file(tmp_path)
        snapshot = make_snapshot(path=str(source))
        assert marker_constraint.test(snapshot) is True

        # removing the marker doesn't matter once the directory is known to hold it
        if marker_constraint.marker.endswith("/"):
            (tmp_path / marker_constraint.marker).rmdir()
        else:
            (tmp_path / marker_constraint.marker).unlink()
        assert marker_constraint.test(snapshot) is True

    def test_each_constraint_remembers_only_its_own_directories(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_go_project import IsGoProjectConstraint
        from plugin.rules.constraints.is_rust_project import IsRustProjectConstraint

        IsGoProjectConstraint._found_dirs.clear()
        IsRustProjectConstraint._found_dirs.clear()
        (tmp_path / "go.mod").write_text("")
        snapshot = make_snapshot(path=str(_make_source_file(tmp_path)))

        assert IsGoProjectConstraint().test(snapshot) is True
        assert IsRustProjectConstraint().test(snapshot) is False

    def test_a_directory_marker_must_be_a_directory(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_hg_repo import IsInHgRepoConstraint

        IsInHgRepoConstraint._found_dirs.clear()
        (tmp_path / ".hg").write_text("")  # a file, not the `.hg/` directory

        assert IsInHgRepoConstraint().test(make_snapshot(path=str(_make_source_file(tmp_path)))) is False
