"""Tests for ViewSnapshot and related helper functions."""

import sys
from pathlib import Path

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


class TestGetViewPseudoContentAndFirstLine:
    """Regression: get_view_pseudo_content()/get_view_pseudo_first_line() call
    get_merged_plugin_setting() for "trim_file_size"/"trim_first_line_length" without an explicit
    default, so a key explicitly set to `null` (e.g. a user trying to "unset" an override) used
    to flow straight through as None -- raising TypeError inside head_tail_content_st()'s
    `partial < 0` check, and inside the `max_length >= 0` check here. Both run unconditionally in
    ViewSnapshot.from_view(), which run_auto_set_syntax_on_view() calls for every event."""

    def test_pseudo_content_null_trim_file_size_falls_back_to_default(self, monkeypatch):
        import plugin.settings as settings_mod
        import plugin.snapshot as snapshot_mod

        # simulate the *real* merged-settings layer reporting "trim_file_size" present with
        # value None, then let the real (fixed) get_merged_plugin_setting() run on top of it --
        # mocking get_merged_plugin_setting() itself would bypass the fix being tested
        monkeypatch.setattr(settings_mod, "get_merged_plugin_settings", lambda *a, **kw: {"trim_file_size": None})
        view = _FakeView("hello world")
        assert snapshot_mod.get_view_pseudo_content(view, None) == "hello world"

    def test_pseudo_first_line_null_trim_first_line_length_falls_back_to_default(self, monkeypatch):
        import plugin.settings as settings_mod
        import plugin.snapshot as snapshot_mod

        monkeypatch.setattr(
            settings_mod, "get_merged_plugin_settings", lambda *a, **kw: {"trim_first_line_length": None}
        )
        view = _FakeView("hello world")
        assert snapshot_mod.get_view_pseudo_first_line(view, None) == "hello world"


class TestViewSnapshotConstruction:
    def test_basic_fields(self, make_snapshot):
        snap = make_snapshot(content="hello\nworld", path="/tmp/test.txt")
        assert snap.char_count == 11
        assert snap.line_count == 1  # explicit in factory fixture
        assert snap.path_obj == Path("/tmp/test.txt")
        assert snap.syntax is None
        assert snap.caret_rowcol == (-1, -1)

    def test_lazy_content_default_empty(self, make_snapshot):
        """Content is a regular dataclass field, always present."""
        snap = make_snapshot()
        assert snap.content == ""

    def test_lazy_first_line_default(self, make_snapshot):
        snap = make_snapshot(content="line1\nline2")
        assert snap.first_line == "line1"

    def test_cached_properties_immutable(self, make_snapshot):
        snap = make_snapshot(path="/tmp/foo.py")
        _ = snap.file_extensions  # populate cache
        assert snap.file_extensions == [".py"]

    def test_file_path_property(self, make_snapshot):
        snap = make_snapshot(path="/tmp/foo/bar.txt")
        assert snap.file_path == "/tmp/foo/bar.txt"

    def test_file_path_empty_when_no_path(self, make_snapshot):
        snap = make_snapshot()
        assert snap.file_path == ""

    def test_file_name(self, make_snapshot):
        snap = make_snapshot(path="/tmp/foo.txt")
        assert snap.file_name == "foo.txt"

    def test_file_name_empty_when_no_path(self, make_snapshot):
        snap = make_snapshot()
        assert snap.file_name == ""

    def test_file_name_unhidden(self, make_snapshot):
        snap = make_snapshot(path="/tmp/.hidden")
        assert snap.file_name_unhidden == "hidden"

    def test_line_count(self, make_snapshot):
        snap = make_snapshot(line_count=42)
        assert snap.line_count == 42

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

    def test_valid_view_returns_view(self, make_snapshot):
        snap = make_snapshot()
        # Mock view returns is_valid() == True
        assert snap.valid_view is snap.view

    def test_syntax_none(self, make_snapshot):
        snap = make_snapshot()
        assert snap.syntax is None

    def test_file_size_on_disk(self, make_snapshot):
        snap = make_snapshot(file_size=1024)
        assert snap.file_size == 1024

    def test_file_size_not_on_disk(self, make_snapshot):
        snap = make_snapshot()  # no path, no file_size
        # file_size returns -1 when path_obj is None
        assert snap.file_size == -1


class TestViewSnapshotFileSizeCapturedAtSnapshotTime:
    """`file_size` must be captured once at `from_view()` time, not lazily re-read from disk later."""

    @staticmethod
    def _make_view(monkeypatch, file_path):
        from unittest.mock import MagicMock

        import plugin.snapshot as snapshot_mod

        monkeypatch.setattr(snapshot_mod, "get_view_pseudo_content", lambda view, window: "")
        monkeypatch.setattr(snapshot_mod, "get_view_pseudo_first_line", lambda view, window: "")

        view = MagicMock()
        view.file_name.return_value = str(file_path)
        view.window.return_value = MagicMock()
        view.size.return_value = 0
        view.rowcol.return_value = (0, 0)
        view.sel.return_value = []
        view.encoding.return_value = "UTF-8"
        view.syntax.return_value = None
        return view

    def test_file_size_does_not_reflect_later_disk_changes(self, tmp_path, monkeypatch):
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello")  # 5 bytes
        view = self._make_view(monkeypatch, file_path)

        snap = ViewSnapshot.from_view(view)

        # mutate the file BEFORE ever reading `file_size` -- a lazily-computed value would
        # pick up this new size on first access; a properly captured one must not
        file_path.write_text("hello world, this is now much longer than before")

        assert snap.file_size == 5  # reflects size at snapshot time, not the live file

    def test_file_size_is_minus_one_when_file_does_not_exist(self, tmp_path, monkeypatch):
        """`stat()` raising (deleted/never existed/permission denied) must fall back to -1 and
        leave `path_obj` unset, not just `file_size`."""
        missing_path = tmp_path / "gone.txt"  # never created on disk
        view = self._make_view(monkeypatch, missing_path)

        snap = ViewSnapshot.from_view(view)
        assert snap.file_size == -1
        assert snap.path_obj is None

    def test_path_obj_unset_for_non_regular_file(self, tmp_path, monkeypatch):
        """A directory (or other non-regular file) at the view's path must not be treated as the
        view's on-disk file, even though `stat()` on it succeeds."""
        a_directory = tmp_path / "some_dir"
        a_directory.mkdir()
        view = self._make_view(monkeypatch, a_directory)

        snap = ViewSnapshot.from_view(view)
        assert snap.file_size == -1
        assert snap.path_obj is None


class TestViewSnapshotContentBytes:
    def test_simple_utf8(self, make_snapshot):
        snap = make_snapshot(content="hello")
        assert snap.content_bytes == b"hello"

    def test_unicode_content(self, make_snapshot):
        snap = make_snapshot(content="héllo wörld 🎉")
        assert isinstance(snap.content_bytes, bytes)
        assert snap.content_bytes.decode("utf-8") == "héllo wörld 🎉"


class TestViewSnapshotEdgeCases:
    def test_empty_content(self, make_snapshot):
        snap = make_snapshot(content="")
        assert snap.char_count == 0
        assert snap.first_line == ""

    def test_single_char(self, make_snapshot):
        snap = make_snapshot(content="a")
        assert snap.first_line == "a"

    def test_very_short_path(self, make_snapshot):
        snap = make_snapshot(path="/a.b")
        assert snap.file_name == "a.b"
        assert snap.file_extensions == [".b"]

    def test_no_extension(self, make_snapshot):
        snap = make_snapshot(path="/tmp/Makefile")
        assert snap.file_extensions == []
