"""Tests for ViewSnapshot and related helper functions."""

import sys
from pathlib import Path

from plugin.snapshot import ViewSnapshot


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
