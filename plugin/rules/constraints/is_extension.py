from ...helper import generate_trimmed_strings
from ...settings import pref_trim_suffixes
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException
from typing import Any, Tuple
import sublime


def extensionize(ext: str) -> str:
    """Ensure extensions are prefixed with a dot."""
    return f".{ext}" if ext[0].isalpha() else ext


class IsExtensionConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.exts: Tuple[str, ...] = self._handled_args(extensionize)

    def is_droppable(self) -> bool:
        return not self.exts

    def test(self, view: sublime.View) -> bool:
        if not (window := view.window()):
            raise AlwaysFalsyException("view has been closed")

        return any(
            filename.endswith(self.exts)
            for filename in generate_trimmed_strings(
                self.get_view_info(view)["file_name"],
                pref_trim_suffixes(window),
            )
        )
