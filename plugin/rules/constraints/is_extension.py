from ...helper import generate_trimmed_strings
from ...helper import is_using_case_insensitive_os
from ...settings import pref_trim_suffixes
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException
from typing import Any, Tuple, final
import sublime


def _extensionize(ext: str) -> str:
    """Ensure extensions are prefixed with a dot."""
    return f".{ext}" if ext[0].isalpha() else ext


@final
class IsExtensionConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.case_insensitive = bool(kwargs.get("case_insensitive", is_using_case_insensitive_os()))
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
                generate_trimmed_strings(
                    self.get_view_info(view)["file_name"],
                    pref_trim_suffixes(window=window),
                ),
            )
        )

    def fix_case(self, string: str) -> str:
        return string.lower() if self.case_insensitive else string
