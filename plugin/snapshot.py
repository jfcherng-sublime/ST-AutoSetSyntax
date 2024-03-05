from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import sublime

from .settings import get_merged_plugin_setting
from .utils import head_tail_content_st


@dataclass
class ViewSnapshot:
    view: sublime.View
    """The view object."""
    char_count: int
    """Character count."""
    content: str
    """Pseudo file content."""
    first_line: str
    """Pseudo first line."""
    line_count: int
    """Number of lines in the original content."""
    path_obj: Path | None
    """The path object of this file. `None` if not on a disk."""
    syntax: sublime.Syntax | None
    """The syntax object. Note that the value is as-is when it's cached."""
    caret_rowcol: tuple[int, int] = (-1, -1)
    """The 0-indexed `(row, column)` of the first caret visually. -1 if no caret."""

    @property
    def file_extensions(self) -> list[str]:
        """The file extensions. Empty list if not on a disk."""
        return self.path_obj.suffixes if self.path_obj else []

    @property
    def file_name(self) -> str:
        """The file name. Empty string if not on a disk."""
        return self.path_obj.name if self.path_obj else ""

    @property
    def file_name_unhidden(self) -> str:
        """The file name without prefixed dots. Empty string if not on a disk."""
        return self.file_name.lstrip(".")

    @property
    def file_path(self) -> str:
        """The full file path with `/` as the directory separator. Empty string if not on a disk."""
        return self.path_obj.as_posix() if self.path_obj else ""

    @property
    def file_size(self) -> int:
        """The file size in bytes, -1 if file not on a disk."""
        return self.path_obj.stat().st_size if self.path_obj else -1

    @property
    def valid_view(self) -> sublime.View | None:
        """The `view` object if it's still valid, otherwise `None`."""
        return self.view if self.view.is_valid() else None

    @classmethod
    def from_view(cls, view: sublime.View) -> ViewSnapshot:
        """Create a `ViewSnapshot` object from a `sublime.View` object."""
        window = view.window() or sublime.active_window()

        # is real file on a disk?
        if (_path := view.file_name()) and (path := Path(_path).resolve()).is_file():
            pass
        else:
            path = None

        return cls(
            view=view,
            char_count=view.size(),
            content=get_view_pseudo_content(view, window),
            first_line=get_view_pseudo_first_line(view, window),
            line_count=view.rowcol(view.size())[0] + 1,
            path_obj=path,
            syntax=view.syntax(),
            caret_rowcol=view.rowcol(sels[0].b) if len(sels := view.sel()) else (-1, -1),
        )


def get_view_pseudo_content(view: sublime.View, window: sublime.Window) -> str:
    return head_tail_content_st(view, get_merged_plugin_setting("trim_file_size", window=window))


def get_view_pseudo_first_line(view: sublime.View, window: sublime.Window) -> str:
    region = view.line(0)
    if (max_length := get_merged_plugin_setting("trim_first_line_length", window=window)) >= 0:
        region.b = min(region.b, max_length)
    return view.substr(region)
