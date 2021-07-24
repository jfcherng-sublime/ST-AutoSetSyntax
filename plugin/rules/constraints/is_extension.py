from ...helper import generate_trimmed_string
from ...settings import pref_trim_suffixes
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException
from typing import Any, Tuple
import sublime


class IsExtensionConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.exts: Tuple[str, ...] = tuple(
            map(
                # ensure extensions are prefixed with a single dot
                lambda ext: f".{ext}" if ext[0].isalpha() else ext,
                filter(None, self.args),  # remove empty string if any
            )
        )

    def is_droppable(self) -> bool:
        return not self.exts

    def test(self, view: sublime.View) -> bool:
        if not (window := view.window()):
            raise AlwaysFalsyException("view has been closed")

        return any(
            filename.endswith(self.exts)
            for filename in generate_trimmed_string(
                self.get_view_info(view)["file_name"],
                pref_trim_suffixes(window),
            )
        )
