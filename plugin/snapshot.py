from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Self

import sublime

from .encodings import from_sublime as encoding_from_sublime
from .settings import get_merged_plugin_setting
from .utils import head_tail_content_st


@dataclass(frozen=True)
class ViewSnapshot:
    view: sublime.View
    """The view object."""
    char_count: int
    """Character count."""
    encoding: str
    """The encoding name, in Sublime Text's definition, of the content."""
    line_count: int
    """Number of lines in the original content."""
    path_obj: Path | None
    """The path object of this file. `None` if not on a disk."""
    syntax: sublime.Syntax | None
    """The syntax object. Note that the value is as-is when it's cached."""
    caret_rowcol: tuple[int, int] = (-1, -1)
    """The 0-indexed `(row, column)` of the first caret visually. -1 if no caret."""

    # Settings captured at snapshot time; used for lazy content/first_line.
    # Defined as fields so the frozen dataclass init sets them, but marked repr=False
    # to keep debug output clean.
    _trim_file_size: int = 0
    """Snapshot of the `trim_file_size` setting."""
    _trim_first_line_length: int = -1
    """Snapshot of the `trim_first_line_length` setting."""

    def __post_init__(self) -> None:
        # for unsaved buffer, ST returns "Undefined" for its encoding
        if self.encoding == "Undefined":
            super().__setattr__("encoding", "UTF-8")

    # ── Lazily-computed fields ─────────────────────────────────────

    @cached_property
    def content(self) -> str:
        """Pseudo file content, computed lazily on first access."""
        return head_tail_content_st(self.view, self._trim_file_size)

    @cached_property
    def first_line(self) -> str:
        """Pseudo first line, computed lazily on first access."""
        region = self.view.line(0)
        if self._trim_first_line_length >= 0:
            region.b = min(region.b, self._trim_first_line_length)
        return self.view.substr(region)

    # ── Derived cached properties ──────────────────────────────────

    @cached_property
    def content_bytes(self) -> bytes:
        """The `bytes` representation of the content."""
        return self.content.encode(self.encoding_py)

    @cached_property
    def encoding_py(self) -> str:
        """The encoding name in Python's definition."""
        return encoding_from_sublime(self.encoding)

    @cached_property
    def file_extensions(self) -> list[str]:
        """The file extensions. Empty list if not on a disk."""
        return self.path_obj.suffixes if self.path_obj else []

    @cached_property
    def file_name(self) -> str:
        """The file name. Empty string if not on a disk."""
        return self.path_obj.name if self.path_obj else ""

    @cached_property
    def file_name_unhidden(self) -> str:
        """The file name without prefixed dots. Empty string if not on a disk."""
        return self.file_name.lstrip(".")

    @cached_property
    def file_path(self) -> str:
        """The full file path with `/` as the directory separator. Empty string if not on a disk."""
        return self.path_obj.as_posix() if self.path_obj else ""

    @cached_property
    def file_size(self) -> int:
        """The file size in bytes, `-1` if file not on a disk."""
        return self.path_obj.stat().st_size if self.path_obj else -1

    @property
    def valid_view(self) -> sublime.View | None:
        """The `view` object if it's still valid, otherwise `None`."""
        return self.view if self.view.is_valid() else None

    @classmethod
    def from_view(cls, view: sublime.View) -> Self:
        """Create a `ViewSnapshot` object from a `sublime.View` object."""
        window = view.window() or sublime.active_window()

        # is real file on a disk?
        if not (_path := view.file_name()) or not (path := Path(_path).resolve()).is_file():
            path = None

        return cls(
            view=view,
            char_count=view.size(),
            encoding=view.encoding(),
            line_count=view.rowcol(view.size())[0] + 1,
            path_obj=path,
            syntax=view.syntax(),
            caret_rowcol=view.rowcol(sels[0].b) if len(sels := view.sel()) else (-1, -1),
            _trim_file_size=get_merged_plugin_setting("trim_file_size", window=window),
            _trim_first_line_length=get_merged_plugin_setting("trim_first_line_length", window=window),
        )
