from __future__ import annotations

from typing import Any, Tuple, final

import sublime

from ...settings import pref_trim_suffixes
from ...utils import list_trimmed_strings
from ..constraint import AbstractConstraint, AlwaysFalsyException


def _extensionize(ext: str) -> str:
    """Ensure extensions are prefixed with a dot."""
    return f".{ext}" if ext[0].isalpha() else ext


@final
class IsExtensionConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.case_insensitive = self._handled_case_insensitive(kwargs)
        self.exts: Tuple[str, ...] = self._handled_args(_extensionize)
        self.exts = tuple(map(self.fix_case, self.exts))

    def is_droppable(self) -> bool:
        return not self.exts

    def test(self, view: sublime.View) -> bool:
        if not (window := view.window()):
            raise AlwaysFalsyException("view has been closed")

        return any(
            filename.endswith(self.exts)
            for filename in map(
                self.fix_case,
                list_trimmed_strings(
                    self.get_view_snapshot(view).file_name,
                    pref_trim_suffixes(window=window),
                ),
            )
        )

    def fix_case(self, string: str) -> str:
        return string.lower() if self.case_insensitive else string
