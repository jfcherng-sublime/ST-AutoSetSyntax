from typing import Any, Tuple, final

import sublime

from ..constraint import AbstractConstraint


@final
class ContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()
        self.threshold: int = kwargs.get("threshold", 1)

    def is_droppable(self) -> bool:
        return not (self.needles and isinstance(self.threshold, (int, float)))

    def test(self, view: sublime.View) -> bool:
        content = self.get_view_info(view)["content"]
        length = len(content)
        count = 0
        for needle in self.needles:
            cursor = 0
            while cursor < length and (idx := content.find(needle, cursor)) != -1:
                count += 1
                if count >= self.threshold:
                    return True
                cursor += idx + len(needle)
        return False
