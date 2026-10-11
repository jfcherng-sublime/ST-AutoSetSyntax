from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class SomeMatch(AbstractMatch):
    """Matches some like `(5,)`, which means at least 5 rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # reject rather than default: a missing/negative count used to mean "satisfied by nothing",
        # i.e. a typo made the rule match every file. Raising makes the whole rule invalid instead
        if not (len(self.args) == 1 and _is_count(count := self.args[0])):
            raise ValueError(f'"some" needs exactly one argument, a non-negative integer count, got {list(self.args)}')
        self.count: int = count

    @override
    def fold(self, rules: tuple[MatchableRule, ...]) -> Fold:
        """
        `some(0)` makes `test_count()` short-circuit on its `goal <= 0` check, so the match is a
        constant True no matter how many rules it has. A count above the rule count can never be
        reached: constant False.
        """
        if self.count == 0:
            return Fold(True, 'a "some" count of 0 is met without any sub-rule passing')
        if self.count > len(rules):
            return Fold(False, f'a "some" count of {self.count} needs more than the {len(rules)} sub-rule(s) given')
        return UNFOLDED

    # prunable_child_value() is intentionally NOT overridden. `some(n)`'s goal `n` is a fixed
    # literal, independent of how many rules it has (unlike `ratio`), so dropping a
    # constant-False child -- one that could never contribute toward reaching `n` -- never
    # changes whether `n` is reachable. The inherited default (only constant-False is prunable)
    # is exactly right here.

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, self.count)


def _is_count(value: Any) -> bool:
    # `bool` is an `int` subclass, but `true` in settings is surely not meant as a count of 1
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
