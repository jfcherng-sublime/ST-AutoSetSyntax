from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class SomeMatch(AbstractMatch):
    """Matches some like `(5,)`, which means at least 5 rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.count: float = nth(self.args, 0) or -1

    @override
    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return not (0 <= self.count <= len(rules))

    @override
    def droppable_value(self, rules: tuple[MatchableRule, ...]) -> bool:
        """A negative count always satisfies `goal <= 0` (constant True); count > len(rules) can never be satisfied."""
        return self.count <= 0

    # prunable_child_value() is intentionally NOT overridden. `some(n)`'s goal `n` is a fixed
    # literal, independent of how many rules it has (unlike `ratio`), so dropping a
    # constant-False child -- one that could never contribute toward reaching `n` -- never
    # changes whether `n` is reachable. The inherited default (only constant-False is prunable)
    # is exactly right here.

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, self.count)
