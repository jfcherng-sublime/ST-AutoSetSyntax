from __future__ import annotations

import uuid
from collections import UserDict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import sublime

from .constants import VIEW_RUN_ID_SETTINGS_KEY
from .settings import get_merged_plugin_setting
from .utils import get_view_by_id, head_tail_content_st


@dataclass
class ViewSnapshot:
    id: int
    """View ID."""
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
    def view(self) -> sublime.View | None:
        return get_view_by_id(self.id)


# `UserDict` is not subscriptable until Python 3.9...
if TYPE_CHECKING:
    _UserDict_ViewSnapshot = UserDict[str, ViewSnapshot]
else:
    _UserDict_ViewSnapshot = UserDict


class ViewSnapshotCollection(_UserDict_ViewSnapshot):
    def add(self, cache_id: str, view: sublime.View) -> None:
        window = view.window() or sublime.active_window()

        # is real file on a disk?
        if (_path := view.file_name()) and (path := Path(_path).resolve()).is_file():
            pass
        else:
            path = None

        self[cache_id] = ViewSnapshot(
            id=view.id(),
            char_count=view.size(),
            content=get_view_pseudo_content(view, window),
            first_line=get_view_pseudo_first_line(view, window),
            line_count=view.rowcol(view.size())[0] + 1,
            path_obj=path,
            syntax=view.syntax(),
            caret_rowcol=view.rowcol(sels[0].b) if len(sels := view.sel()) else (-1, -1),
        )

    def get_by_view(self, view: sublime.View) -> ViewSnapshot | None:
        return self.get(view.settings().get(VIEW_RUN_ID_SETTINGS_KEY))

    @contextmanager
    def snapshot_context(self, view: sublime.View) -> Generator[ViewSnapshot, None, None]:
        run_id = str(uuid.uuid4())
        settings = view.settings()

        try:
            settings.set(VIEW_RUN_ID_SETTINGS_KEY, run_id)
            self.add(run_id, view)
            yield self.get(run_id)  # type: ignore
        finally:
            settings.erase(VIEW_RUN_ID_SETTINGS_KEY)
            self.pop(run_id)


def get_view_pseudo_content(view: sublime.View, window: sublime.Window) -> str:
    return head_tail_content_st(view, get_merged_plugin_setting("trim_file_size", window=window))


def get_view_pseudo_first_line(view: sublime.View, window: sublime.Window) -> str:
    region = view.line(0)
    if (max_length := get_merged_plugin_setting("trim_first_line_length", window=window)) >= 0:
        region = sublime.Region(region.a, min(region.b, max_length))
    return view.substr(region)
