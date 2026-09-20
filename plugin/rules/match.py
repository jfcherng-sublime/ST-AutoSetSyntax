from abc import ABC
from abc import abstractmethod
from collections.abc import Generator
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Self
from typing import final
from typing import override

from more_itertools import first_true

from ..cache import clearable_lru_cache
from ..logger import Logger
from ..snapshot import ViewSnapshot
from ..types import Optimizable
from ..types import StConstraintRule
from ..types import StMatchRule
from ..utils import camel_to_snake
from ..utils import drop_falsy
from ..utils import list_all_subclasses
from .constraint import ConstraintRule


def find_match(obj: Any) -> type[AbstractMatch] | None:
    return first_true(get_matches(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_matches() -> tuple[type[AbstractMatch], ...]:
    return tuple(sorted(list_matches(), key=lambda cls: cls.name()))


def list_matches() -> Generator[type[AbstractMatch]]:
    yield from list_all_subclasses(AbstractMatch, skip_abstract=True)  # type: ignore[type-abstract]


@dataclass(slots=True)
class MatchRule(Optimizable):
    match: AbstractMatch | None = None
    match_name: str = ""
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    rules: tuple[MatchableRule, ...] = ()

    src_setting: StMatchRule | None = None
    """The source setting object."""

    @override
    def fold(self) -> bool | None:
        if not self.match:
            return False  # a match rule that failed to compile can never pass

        value = self.match.fold(self.rules)
        if value is None and not self.rules:
            # whatever the combinator, a match with no child rules can't depend on the view;
            # `False` mirrors what a match that doesn't say what it folds to used to collapse to
            return False
        return value

    @override
    def optimize(self) -> Generator[Optimizable]:
        assert self.match

        for rule in self.rules:
            yield from rule.optimize()

        prunable_value = self.match.prunable_child_value()
        if prunable_value is None:
            # this combinator's result depends on how many rules it has (e.g. ratio), so no
            # child -- even a folded/constant one -- can ever be safely removed from `rules`
            return

        survivors: list[MatchableRule] = []
        for rule in self.rules:
            # a rule that doesn't fold compares as `None` here, so it's never pruned
            if rule.fold() == prunable_value:
                yield rule
            else:
                survivors.append(rule)
        self.rules = tuple(survivors)

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.match
        return self.match.test(view_snapshot, self.rules)

    @classmethod
    def make(cls, match_rule: StMatchRule) -> Self | None:
        """Build this object with the `match_rule`."""
        match = match_rule.match
        if not (match_class := find_match(match)):
            Logger.log(f"❌ Unsupported match rule: {match}")
            return None

        def make_matchable_rule(rule: StConstraintRule | StMatchRule) -> MatchableRule | None:
            match rule:
                case StConstraintRule():
                    return ConstraintRule.make(rule)
                case StMatchRule():
                    return MatchRule.make(rule)

        try:
            match_obj = match_class(*match_rule.args, **match_rule.kwargs)
        except Exception as e:
            Logger.log(f"❌ Failed to create match {match}({match_rule.args}, {match_rule.kwargs}): {e}")
            return None

        return cls(
            match=match_obj,
            match_name=match,
            args=tuple(match_rule.args),
            kwargs=match_rule.kwargs,
            rules=tuple(drop_falsy(map(make_matchable_rule, match_rule.rules))),
            src_setting=match_rule,
        )


# rules that can be used in a match rule
type MatchableRule = ConstraintRule | MatchRule


class AbstractMatch(ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @final
    @classmethod
    def name(cls) -> str:
        """The nickname of this class. Converts "FooBarMatch" into "foo_bar" by default."""
        return camel_to_snake(cls.__name__.removesuffix("Match"))

    @final
    @classmethod
    def can_support(cls, obj: Any) -> bool:
        """Determines whether this class supports `obj`."""
        return str(obj) == cls.name()

    def fold(self, rules: tuple[MatchableRule, ...]) -> bool | None:
        """
        The fixed boolean value `test()` always returns for `rules`, or `None` when the result
        still depends on the view (see `Optimizable.fold()` for the general contract).

        Override this whenever this combinator's own parameters and rule *count* already settle
        the answer, in either direction: `all([])` is a constant `True` and `any([])` a constant
        `False`, while `some(n)` is a constant `True` when `n <= 0` and a constant `False` when
        `n` exceeds the rule count.
        """
        return None

    def prunable_child_value(self) -> bool | None:
        """
        Which constant a folded child rule must fold to for it to be safely removable from
        `rules` without changing this match's own result -- i.e. this combinator's identity
        element.

        `MatchRule.optimize()` calls this to decide what it may prune from a `MatchRule`'s
        children: a child is removed only when its `fold()` equals this value. A child folding
        to the *other* constant must stay in `rules` so it keeps contributing its fixed result
        at test time -- dropping it would silently change what this match evaluates to.

        For example, `True` is safe to drop from `all(...)` (AND's identity element:
        `all(True, is_extension("py")) == all(is_extension("py"))`), but `False` is not
        (`all(False, is_extension("py"))` is always `False`, unlike `all(is_extension("py"))`,
        which depends on the file). Silently deleting a constant-`False` child from an `all` --
        rather than leaving it in place or collapsing the whole match to `False` -- is exactly
        the bug this method exists to prevent.

        Return `None` when NO child can ever be safely removed, regardless of what it folds to
        -- i.e. this match's result depends on how many children it has, not just their
        individual values. `RatioMatch` returns `None`: its goal is `ceil(ratio * len(rules))`,
        so removing any child -- constant or not -- shifts that goal.

        Defaults to `False` (safe to drop a constant-`False` child), which is correct for `any`
        (OR: `False` is the identity element) and for a fixed-goal `some(n)` (removing a rule
        that could never contribute toward reaching `n` doesn't change whether `n` is reachable).
        """
        return False

    @abstractmethod
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        """Tests whether the `view_snapshot` passes this `match` with those `rules`."""

    @final
    @staticmethod
    def test_count(view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...], goal: float) -> bool:
        """Tests whether the amount of passing `rules` is greater than or equal to `goal`."""
        if goal <= 0:
            return True

        tolerance = len(rules) - goal  # how many rules can be failed at most
        for rule in rules:
            if tolerance < 0:
                return False
            if rule.test(view_snapshot):
                goal -= 1
                if goal <= 0:
                    return True
            else:
                tolerance -= 1
        return False
