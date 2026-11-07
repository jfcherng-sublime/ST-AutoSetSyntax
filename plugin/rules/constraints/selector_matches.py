from typing import Any
from typing import Final
from typing import final
from typing import override

import sublime

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class SelectorMatchesConstraint(AbstractConstraint):
    args_noun = "selector"
    needs_syntax = True

    SCORE_THRESHOLD: Final[int] = 1
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

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert view_snapshot.syntax
        return any(
            # ...
            sublime.score_selector(view_snapshot.syntax.scope, candidate) >= self.SCORE_THRESHOLD
            for candidate in self.candidates
        )
