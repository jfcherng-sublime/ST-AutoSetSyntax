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

    def test_name(self):
        from plugin.rules.constraints.relative_exists import RelativeExistsConstraint

        assert RelativeExistsConstraint.name() == "relative_exists"


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
    def test_enabled(self, make_snapshot):
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=True):
            assert IsMagikaEnabledConstraint().test(snap) is True

    def test_disabled(self, make_snapshot):
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=False):
            assert IsMagikaEnabledConstraint().test(snap) is False

    def test_default_disabled(self, make_snapshot):
        from unittest.mock import patch

        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        snap = make_snapshot()
        with patch("plugin.rules.constraints.is_magika_enabled.get_merged_plugin_setting", return_value=None):
            assert IsMagikaEnabledConstraint().test(snap) is False

    def test_name(self):
        from plugin.rules.constraints.is_magika_enabled import IsMagikaEnabledConstraint

        assert IsMagikaEnabledConstraint.name() == "is_magika_enabled"
