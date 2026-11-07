"""Tests for ViewSnapshot and related helper functions."""

import sys

from conftest import DEFAULT_SETTINGS

from plugin.snapshot import ViewSnapshot


class _FakeView:
    def __init__(self, content: str) -> None:
        self._content = content

    def size(self) -> int:
        return len(self._content)

    def substr(self, region) -> str:
        return self._content[region.a : region.b]

    def line(self, pt: int):
        import sublime

        return sublime.Region(0, len(self._content))


class TestHeadTailContentSt:
    def test_content_between_half_and_partial_is_not_duplicated(self):
        """Regression: with `half < size <= partial` the head and the tail overlapped, so the
        middle appeared twice."""
        from plugin.utils import head_tail_content_st

        assert head_tail_content_st(_FakeView("aaaaFOObbbb"), 20) == "aaaaFOObbbb"

    def test_content_longer_than_partial_is_split(self):
        from plugin.utils import head_tail_content_st

        assert head_tail_content_st(_FakeView("abcdefghij1234567890X"), 20) == "abcdefghij\n\n234567890X"


class TestViewSnapshotConstruction:
    def test_file_path_property(self, make_snapshot):
        snap = make_snapshot(path="/tmp/foo/bar.txt")
        assert snap.file_path == "/tmp/foo/bar.txt"

    def test_file_name(self, make_snapshot):
        snap = make_snapshot(path="/tmp/foo.txt")
        assert snap.file_name == "foo.txt"

    def test_path_properties_are_empty_when_no_path(self, make_snapshot):
        snap = make_snapshot()
        assert (snap.file_path, snap.file_name) == ("", "")

    def test_file_name_unhidden(self, make_snapshot):
        snap = make_snapshot(path="/tmp/.hidden")
        assert snap.file_name_unhidden == "hidden"

    def test_encoding_undefined_normalized(self):
        """Encoding 'Undefined' should be normalized to 'UTF-8'."""
        MockView = sys.modules["sublime"].View
        snap = ViewSnapshot(
            view=MockView(),
            char_count=0,
            content="",
            first_line="",
            encoding="Undefined",
            line_count=0,
            path_obj=None,
            syntax=None,
        )
        assert snap.encoding == "UTF-8"

    def test_encoding_py_lookup(self, make_snapshot):
        snap = make_snapshot(encoding="Western (Windows 1252)")
        assert snap.encoding_py == "cp1252"

    def test_valid_view_is_none_once_the_view_is_gone(self, make_snapshot):
        snap = make_snapshot()
        assert snap.valid_view is snap.view
        snap.view.is_valid = lambda: False
        assert snap.valid_view is None


class TestViewSnapshotFileSizeCapturedAtSnapshotTime:
    """`file_size` must be captured once at `from_view()` time, not lazily re-read from disk later."""

    @staticmethod
    def _make_view(monkeypatch, file_path):
        from unittest.mock import MagicMock

        import sublime

        import plugin.snapshot as snapshot_mod

        monkeypatch.setattr(snapshot_mod, "head_tail_content_st", lambda view, partial: "")

        view = MagicMock()
        view.file_name.return_value = str(file_path)
        view.window.return_value = MagicMock()
        view.size.return_value = 0
        view.line.return_value = sublime.Region(0, 0)
        view.substr.return_value = ""
        view.rowcol.return_value = (0, 0)
        view.sel.return_value = []
        view.encoding.return_value = "UTF-8"
        view.syntax.return_value = None
        return view

    def test_file_size_does_not_reflect_later_disk_changes(self, tmp_path, monkeypatch):
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello")  # 5 bytes
        view = self._make_view(monkeypatch, file_path)

        snap = ViewSnapshot.from_view(view, DEFAULT_SETTINGS)

        # mutate the file BEFORE ever reading `file_size` -- a lazily-computed value would
        # pick up this new size on first access; a properly captured one must not
        file_path.write_text("hello world, this is now much longer than before")

        assert snap.file_size == 5  # reflects size at snapshot time, not the live file

    def test_file_size_is_minus_one_when_file_does_not_exist(self, tmp_path, monkeypatch):
        """`stat()` raising (deleted/never existed/permission denied) must fall back to -1 and
        leave `path_obj` unset, not just `file_size`."""
        missing_path = tmp_path / "gone.txt"  # never created on disk
        view = self._make_view(monkeypatch, missing_path)

        snap = ViewSnapshot.from_view(view, DEFAULT_SETTINGS)
        assert snap.file_size == -1
        assert snap.path_obj is None

    def test_path_obj_unset_for_non_regular_file(self, tmp_path, monkeypatch):
        """A directory (or other non-regular file) at the view's path must not be treated as the
        view's on-disk file, even though `stat()` on it succeeds."""
        a_directory = tmp_path / "some_dir"
        a_directory.mkdir()
        view = self._make_view(monkeypatch, a_directory)

        snap = ViewSnapshot.from_view(view, DEFAULT_SETTINGS)
        assert snap.file_size == -1
        assert snap.path_obj is None


class TestViewSnapshotContentBytes:
    def test_content_bytes_are_utf8(self, make_snapshot):
        assert make_snapshot(content="héllo wörld 🎉").content_bytes == "héllo wörld 🎉".encode()


class TestViewSnapshotEdgeCases:
    def test_very_short_path(self, make_snapshot):
        snap = make_snapshot(path="/a.b")
        assert snap.file_name == "a.b"
        assert snap.file_extensions == [".b"]

    def test_no_extension(self, make_snapshot):
        snap = make_snapshot(path="/tmp/Makefile")
        assert snap.file_extensions == []
