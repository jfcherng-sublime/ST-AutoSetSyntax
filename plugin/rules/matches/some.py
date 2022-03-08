from ...helper import get_nth_item
from ..match import AbstractMatch
from ..match import MatchableRule
from typing import Any, Tuple, final
import sublime


@final
class SomeMatch(AbstractMatch):
    """Matches some like `(5,)`, which means at least 5 rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.count: float = get_nth_item(self.args, 0) or -1

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        return not (0 <= self.count <= len(rules))

    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view, rules, self.count)
