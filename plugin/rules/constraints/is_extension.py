from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...utils import list_trimmed_strings
from ..constraint import AbstractConstraint


def _extensionize(ext: str) -> str:
    """Ensure extensions are prefixed with a dot."""
    return f".{ext}" if not ext.startswith(".") else ext


@final
class IsExtensionConstraint(AbstractConstraint):
    args_noun = "extension"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fix_case = self._handled_case_folder(kwargs)
        self.exts: tuple[str, ...] = tuple(map(self.fix_case, self._handled_args(_extensionize)))

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return any(
            filename.endswith(self.exts)
            for filename in map(
                self.fix_case,
                list_trimmed_strings(view_snapshot.file_name, view_snapshot.trim_suffixes),
            )
        )
