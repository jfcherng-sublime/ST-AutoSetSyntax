"""Tests for constraints that need real filesystem paths (repo detection, relative_exists)."""

import pytest


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

    def test_no_file_path_raises(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        snap = make_snapshot()  # path=None
        with pytest.raises(AlwaysFalsyException):
            RelativeExistsConstraint("anything").test(snap)

    def test_empty_args_is_droppable(self):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        assert RelativeExistsConstraint().is_droppable() is True

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
        assert constraint.match == "any"
        assert constraint.test(snap) is True

    def test_name(self):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        assert RelativeExistsConstraint.name() == "relative_exists"


class TestFindParentWithSiblingCached:
    """find_parent_with_sibling_cached() is the shared implementation behind
    IsInGitRepoConstraint/IsInHgRepoConstraint/IsInSvnRepoConstraint/
    IsInRubyOnRailsProjectConstraint's test() methods. The constraint-specific test classes below
    only exercise the underlying find_parent_with_sibling() static helper, not this wrapper's own
    behavior (the AlwaysFalsyException guard and the cache hit/miss/populate logic), so it's
    covered directly here once instead of duplicating it four times."""

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        snap = make_snapshot()  # no path
        with pytest.raises(AlwaysFalsyException):
            IsInGitRepoConstraint().find_parent_with_sibling_cached(snap, set(), ".git", use_exists=True)

    def test_cache_hit_short_circuits_without_filesystem_match(self, make_snapshot, tmp_path):
        """A parent directory already in the cache set must return True even though the sibling
        doesn't actually exist on disk -- proving the cache path, not a fresh scan, was taken."""
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        test_file = tmp_path / "sub" / "main.py"
        test_file.parent.mkdir()
        test_file.write_text("")
        snap = make_snapshot(path=str(test_file))

        cache = {tmp_path}
        result = IsInGitRepoConstraint().find_parent_with_sibling_cached(
            snap, cache, "this-sibling-does-not-exist", use_exists=True
        )
        assert result is True

    def test_cache_miss_with_match_populates_the_cache(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        (tmp_path / ".git").mkdir()
        test_file = tmp_path / "sub" / "main.py"
        test_file.parent.mkdir()
        test_file.write_text("")
        snap = make_snapshot(path=str(test_file))

        cache: set = set()
        result = IsInGitRepoConstraint().find_parent_with_sibling_cached(snap, cache, ".git", use_exists=True)

        assert result is True
        assert tmp_path in cache

    def test_cache_miss_without_match_leaves_cache_empty(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        test_file = tmp_path / "sub" / "main.py"
        test_file.parent.mkdir()
        test_file.write_text("")
        snap = make_snapshot(path=str(test_file))

        cache: set = set()
        result = IsInGitRepoConstraint().find_parent_with_sibling_cached(snap, cache, ".git", use_exists=True)

        assert result is False
        assert cache == set()


class TestIsInGitRepoConstraint:
    def test_dot_git_directory(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        # Create a temp git repo-like structure
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        test_file = tmp_path / "code.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInGitRepoConstraint().test(snap) is True

    def test_dot_git_file_worktree(self, make_snapshot, tmp_path):
        """Git worktrees use a .git FILE, not directory."""
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /some/worktree\n")
        test_file = tmp_path / "code.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInGitRepoConstraint().test(snap) is True

    def test_not_in_repo(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        test_file = tmp_path / "code.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInGitRepoConstraint().test(snap) is False

    def test_nested_in_repo(self, make_snapshot, tmp_path):
        """File in a subdirectory of a repo should also match."""
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "src" / "app"
        subdir.mkdir(parents=True)
        test_file = subdir / "main.py"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInGitRepoConstraint().test(snap) is True

    def test_name(self):
        from plugin.rules.constraints.is_in_git_repo import IsInGitRepoConstraint

        assert IsInGitRepoConstraint.name() == "is_in_git_repo"


class TestIsInHgRepoConstraint:
    def test_dot_hg_directory(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_hg_repo import IsInHgRepoConstraint

        hg_dir = tmp_path / ".hg"
        hg_dir.mkdir()
        test_file = tmp_path / "file.txt"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInHgRepoConstraint().test(snap) is True

    def test_not_in_hg_repo(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_hg_repo import IsInHgRepoConstraint

        test_file = tmp_path / "file.txt"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInHgRepoConstraint().test(snap) is False

    def test_name(self):
        from plugin.rules.constraints.is_in_hg_repo import IsInHgRepoConstraint

        assert IsInHgRepoConstraint.name() == "is_in_hg_repo"


class TestIsInSvnRepoConstraint:
    def test_dot_svn_directory(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_svn_repo import IsInSvnRepoConstraint

        svn_dir = tmp_path / ".svn"
        svn_dir.mkdir()
        test_file = tmp_path / "file.txt"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInSvnRepoConstraint().test(snap) is True

    def test_not_in_svn_repo(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_in_svn_repo import IsInSvnRepoConstraint

        test_file = tmp_path / "file.txt"
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsInSvnRepoConstraint().test(snap) is False

    def test_name(self):
        from plugin.rules.constraints.is_in_svn_repo import IsInSvnRepoConstraint

        assert IsInSvnRepoConstraint.name() == "is_in_svn_repo"


class TestIsGoProjectConstraint:
    def test_go_mod_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        go_mod = tmp_path / "go.mod"
        go_mod.write_text("")
        test_file = tmp_path / "cmd" / "main.go"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "go.mod", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_go_mod_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        go_mod = tmp_path / "go.mod"
        go_mod.write_text("")
        test_file = tmp_path / "cmd" / "main.go"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "go.mod", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_go_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "main.go"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "go.mod", use_exists=False)
        assert result is None

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_go_project import IsGoProjectConstraint

        (tmp_path / "go.mod").write_text("")
        test_file = tmp_path / "internal" / "pkg" / "util.go"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsGoProjectConstraint().test(snap) is True

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_go_project import IsGoProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsGoProjectConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_go_project import IsGoProjectConstraint

        assert IsGoProjectConstraint.name() == "is_go_project"


class TestIsPhpProjectConstraint:
    def test_composer_json_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        composer_json = tmp_path / "composer.json"
        composer_json.write_text("")
        test_file = tmp_path / "src" / "index.php"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "composer.json", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_composer_json_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        composer_json = tmp_path / "composer.json"
        composer_json.write_text("")
        test_file = tmp_path / "src" / "index.php"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "composer.json", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_php_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "index.php"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "composer.json", use_exists=False)
        assert result is None

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_php_project import IsPhpProjectConstraint

        (tmp_path / "composer.json").write_text("")
        test_file = tmp_path / "src" / "Controller" / "HomeController.php"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsPhpProjectConstraint().test(snap) is True

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_php_project import IsPhpProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsPhpProjectConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_php_project import IsPhpProjectConstraint

        assert IsPhpProjectConstraint.name() == "is_php_project"


class TestIsPythonProjectConstraint:
    def test_pyproject_toml_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("")
        test_file = tmp_path / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "pyproject.toml", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_pyproject_toml_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("")
        test_file = tmp_path / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "pyproject.toml", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_python_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "main.py"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "pyproject.toml", use_exists=False)
        assert result is None

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_python_project import IsPythonProjectConstraint

        (tmp_path / "pyproject.toml").write_text("")
        test_file = tmp_path / "src" / "pkg" / "util.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsPythonProjectConstraint().test(snap) is True

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_python_project import IsPythonProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsPythonProjectConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_python_project import IsPythonProjectConstraint

        assert IsPythonProjectConstraint.name() == "is_python_project"


class TestIsRustProjectConstraint:
    def test_cargo_toml_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("")
        test_file = tmp_path / "src" / "main.rs"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "Cargo.toml", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_cargo_toml_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("")
        test_file = tmp_path / "src" / "main.rs"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "Cargo.toml", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_rust_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "main.rs"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "Cargo.toml", use_exists=False)
        assert result is None

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_rust_project import IsRustProjectConstraint

        (tmp_path / "Cargo.toml").write_text("")
        test_file = tmp_path / "src" / "bin" / "util.rs"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsRustProjectConstraint().test(snap) is True

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_rust_project import IsRustProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsRustProjectConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_rust_project import IsRustProjectConstraint

        assert IsRustProjectConstraint.name() == "is_rust_project"


class TestIsTypescriptProjectConstraint:
    def test_tsconfig_json_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        tsconfig_json = tmp_path / "tsconfig.json"
        tsconfig_json.write_text("")
        test_file = tmp_path / "src" / "index.ts"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "tsconfig.json", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_tsconfig_json_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        tsconfig_json = tmp_path / "tsconfig.json"
        tsconfig_json.write_text("")
        test_file = tmp_path / "src" / "index.ts"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "tsconfig.json", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_typescript_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "index.ts"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "tsconfig.json", use_exists=False)
        assert result is None

    def test_nested_in_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_typescript_project import IsTypescriptProjectConstraint

        (tmp_path / "tsconfig.json").write_text("")
        test_file = tmp_path / "src" / "components" / "App.tsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        assert IsTypescriptProjectConstraint().test(snap) is True

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_typescript_project import IsTypescriptProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsTypescriptProjectConstraint().test(snap)

    def test_name(self):
        from plugin.rules.constraints.is_typescript_project import IsTypescriptProjectConstraint

        assert IsTypescriptProjectConstraint.name() == "is_typescript_project"


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

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsJavascriptProjectConstraint().test(snap)

    def test_successful_match_is_cached_for_a_second_file_in_the_same_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        (tmp_path / "package.json").write_text("")
        first_file = tmp_path / "src" / "index.js"
        first_file.parent.mkdir(parents=True)
        first_file.write_text("")
        second_file = tmp_path / "src" / "app.js"
        second_file.write_text("")

        assert IsJavascriptProjectConstraint().test(make_snapshot(path=str(first_file))) is True
        assert tmp_path in IsJavascriptProjectConstraint._successed_dirs
        assert IsJavascriptProjectConstraint().test(make_snapshot(path=str(second_file))) is True

    def test_name(self):
        from plugin.rules.constraints.is_javascript_project import IsJavascriptProjectConstraint

        assert IsJavascriptProjectConstraint.name() == "is_javascript_project"


class TestIsInPythonDjangoProjectConstraint:
    def test_manage_py_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        manage_py = tmp_path / "manage.py"
        manage_py.write_text("")
        test_file = tmp_path / "app" / "models.py"
        test_file.parent.mkdir()
        test_file.write_text("")

        # Test the static find_parent_with_sibling method directly
        found = AbstractConstraint.find_parent_with_sibling(test_file, "manage.py", use_exists=False)
        assert found is not None
        # Verify the constraint works by calling the parent-finding logic
        assert found == tmp_path

    def test_manage_py_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        """Same but using the snapshot file_path as the source."""
        from plugin.rules.constraint import AbstractConstraint

        manage_py = tmp_path / "manage.py"
        manage_py.write_text("")
        test_file = tmp_path / "app" / "models.py"
        test_file.parent.mkdir()
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "manage.py", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_django_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "main.py"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "manage.py", use_exists=False)
        assert result is None

    def test_name(self):
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        assert IsInPythonDjangoProjectConstraint.name() == "is_in_python_django_project"


class TestIsInPythonDjangoProjectConstraintRealTest:
    """The constraint's own `test()` is materially different from (stricter than) the shared
    `find_parent_with_sibling` helper exercised above: it requires *both* a `manage.py` in a
    parent directory *and* a sibling subdirectory of that parent containing all three of
    settings.py/urls.py/wsgi.py (the actual Django-root layout), not just `manage.py` alone.
    None of the tests above actually call this method, so it had no real coverage."""

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

    def test_no_file_on_disk_raises_always_falsy(self, make_snapshot):
        from plugin.rules.constraint import AlwaysFalsyException
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        snap = make_snapshot()  # no path -> not on disk
        with pytest.raises(AlwaysFalsyException):
            IsInPythonDjangoProjectConstraint().test(snap)

    def test_successful_match_is_cached_for_a_second_file_in_the_same_project(self, make_snapshot, tmp_path):
        """A second file under the same project root should hit the `_successed_dirs` fast-path
        cache rather than re-scanning the filesystem."""
        from plugin.rules.constraints.is_in_python_django_project import IsInPythonDjangoProjectConstraint

        self._make_django_project(tmp_path)
        first_file = tmp_path / "myapp" / "models.py"
        first_file.parent.mkdir()
        first_file.write_text("")
        second_file = tmp_path / "myapp" / "views.py"
        second_file.write_text("")

        assert IsInPythonDjangoProjectConstraint().test(make_snapshot(path=str(first_file))) is True
        assert tmp_path in IsInPythonDjangoProjectConstraint._successed_dirs
        assert IsInPythonDjangoProjectConstraint().test(make_snapshot(path=str(second_file))) is True


class TestIsInRubyOnRailsProjectConstraint:
    def test_gemfile_exists(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        gemfile = tmp_path / "Gemfile"
        gemfile.write_text("")
        test_file = tmp_path / "app" / "models" / "user.rb"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        found = AbstractConstraint.find_parent_with_sibling(test_file, "Gemfile", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_gemfile_exists_via_snapshot_path(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        gemfile = tmp_path / "Gemfile"
        gemfile.write_text("")
        test_file = tmp_path / "app" / "models" / "user.rb"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        snap = make_snapshot(path=str(test_file))
        found = AbstractConstraint.find_parent_with_sibling(snap.file_path, "Gemfile", use_exists=False)
        assert found is not None
        assert found == tmp_path

    def test_not_rails_project(self, make_snapshot, tmp_path):
        from plugin.rules.constraint import AbstractConstraint

        test_file = tmp_path / "main.rb"
        test_file.write_text("")

        result = AbstractConstraint.find_parent_with_sibling(test_file, "Gemfile", use_exists=False)
        assert result is None

    def test_name(self):
        from plugin.rules.constraints.is_in_ruby_on_rails_project import IsInRubyOnRailsProjectConstraint

        assert IsInRubyOnRailsProjectConstraint.name() == "is_in_ruby_on_rails_project"


class TestIsMagikaEnabledConstraint:
    def test_enabled_and_usable(self, make_snapshot):
        from unittest.mock import MagicMock
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with (
            patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=True),
            patch("plugin.rules.constraints.is_magika_enabled.get_magika_object", return_value=MagicMock()),
        ):
            assert IsMagikaEnabledConstraint().test(snap) is True

    def test_enabled_but_not_installed(self, make_snapshot):
        """Regression: setting magika.enabled without a working Magika must not report True,
        or the inverted-gated fallback rules (e.g. regex JS detection) get skipped while
        Magika itself never runs -- leaving the file with no syntax."""
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with (
            patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=True),
            patch("plugin.rules.constraints.is_magika_enabled.get_magika_object", return_value=None),
        ):
            assert IsMagikaEnabledConstraint().test(snap) is False

    def test_disabled_short_circuits_without_constructing_magika(self, make_snapshot):
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with (
            patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=False),
            patch("plugin.rules.constraints.is_magika_enabled.get_magika_object") as magika_mock,
        ):
            assert IsMagikaEnabledConstraint().test(snap) is False
        magika_mock.assert_not_called()

    def test_default_disabled(self, make_snapshot):
        from unittest.mock import MagicMock
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with (
            patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=None),
            patch("plugin.rules.constraints.is_magika_enabled.get_magika_object", return_value=MagicMock()),
        ):
            assert IsMagikaEnabledConstraint().test(snap) is False

    def test_name(self):
        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        assert IsMagikaEnabledConstraint.name() == "is_magika_enabled"
