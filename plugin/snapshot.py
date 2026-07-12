import stat
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
    content: str
    """Pseudo file content."""
    first_line: str
    """Pseudo first line."""
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
    file_size: int = -1
    """The file size in bytes, captured at snapshot time. `-1` if not on a disk."""

    def __post_init__(self) -> None:
        # for unsaved buffer, ST returns "Undefined" for its encoding
        if self.encoding == "Undefined":
            super().__setattr__("encoding", "UTF-8")

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

    @property
    def valid_view(self) -> sublime.View | None:
        """The `view` object if it's still valid, otherwise `None`."""
        return self.view if self.view.is_valid() else None

    @classmethod
    def from_view(cls, view: sublime.View) -> Self:
        """Create a `ViewSnapshot` object from a `sublime.View` object."""
        window = view.window() or sublime.active_window()

        # is real file on a disk? Single stat() call does double duty: it both answers that
        # question and gives us file_size, instead of a separate is_file() + stat() pair.
        path: Path | None = None
        file_size = -1
        if path_ := view.file_name():
            candidate = Path(path_).resolve()
            try:
                st = candidate.stat()
            except OSError:
                st = None
            if st is not None and stat.S_ISREG(st.st_mode):
                path = candidate
                file_size = st.st_size

        return cls(
            view=view,
            char_count=view.size(),
            content=get_view_pseudo_content(view, window),
            first_line=get_view_pseudo_first_line(view, window),
            encoding=view.encoding(),
            line_count=view.rowcol(view.size())[0] + 1,
            path_obj=path,
            syntax=view.syntax(),
            caret_rowcol=view.rowcol(sels[0].b) if len(sels := view.sel()) else (-1, -1),
            file_size=file_size,
        )


def get_view_pseudo_content(view: sublime.View, window: sublime.Window) -> str:
    return head_tail_content_st(view, get_merged_plugin_setting("trim_file_size", window=window))


def get_view_pseudo_first_line(view: sublime.View, window: sublime.Window) -> str:
    region = view.line(0)
    if (max_length := get_merged_plugin_setting("trim_first_line_length", window=window)) >= 0:
        region.b = min(region.b, max_length)
    return view.substr(region)
