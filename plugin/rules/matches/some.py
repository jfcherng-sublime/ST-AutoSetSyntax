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

        self.count: float = nth(self.args, 0, -1)

    @override
    def fold(self, rules: tuple[MatchableRule, ...]) -> bool | None:
        """
        A count `<= 0` makes `test_count()` short-circuit on its `goal <= 0` check, so the match
        is a constant True no matter how many rules it has -- note that includes `some(0)`, not
        just a negative count. A count above the rule count can never be reached: constant False.
        """
        if self.count <= 0:
            return True
        if self.count > len(rules):
            return False
        return None

    # prunable_child_value() is intentionally NOT overridden. `some(n)`'s goal `n` is a fixed
    # literal, independent of how many rules it has (unlike `ratio`), so dropping a
    # constant-False child -- one that could never contribute toward reaching `n` -- never
    # changes whether `n` is reachable. The inherited default (only constant-False is prunable)
    # is exactly right here.

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, self.count)
