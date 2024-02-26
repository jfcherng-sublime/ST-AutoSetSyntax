from __future__ import annotations

from typing import Any, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class SelectorMatchesConstraint(AbstractConstraint):
    SCORE_THRESHOLD = 1
    """
    Quick tips (ST >= 4173):

    ```python
    sublime.score_selector("a.b", "b") == 0
    sublime.score_selector("a.b", "")  == 1
    sublime.score_selector("a.b", " ")  == 1
    sublime.score_selector("a.b", "a") == 1
    sublime.score_selector("a.b", "a.b") == 2
    ```

    Quick tips (ST < 4173):

    ```python
    sublime.score_selector("a.b", "b") == 0
    sublime.score_selector("a.b", "")  == 1
    sublime.score_selector("a.b", " ")  == 1
    sublime.score_selector("a.b", "a") == 8
    sublime.score_selector("a.b", "a.b") == 16
    ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.candidates: tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.candidates

    def test(self, view: sublime.View) -> bool:
        if not (syntax := self.get_view_snapshot(view).syntax):
            raise AlwaysFalsyException(f"View({view.id()}) has no syntax")

        return any(
            # ...
            sublime.score_selector(syntax.scope, candidate) >= self.SCORE_THRESHOLD
            for candidate in self.candidates
        )
