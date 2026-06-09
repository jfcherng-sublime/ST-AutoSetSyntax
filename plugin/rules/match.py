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
from ._optimize import sift_optimizable
from .constraint import ConstraintRule


def find_match(obj: Any) -> type[AbstractMatch] | None:
    return first_true(get_matches(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_matches() -> tuple[type[AbstractMatch], ...]:
    return tuple(sorted(list_matches(), key=lambda cls: cls.name()))


def list_matches() -> Generator[type[AbstractMatch]]:
    yield from list_all_subclasses(AbstractMatch, skip_abstract=True)  # type: ignore


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
    def is_droppable(self) -> bool:
        return not (self.rules and self.match and not self.match.is_droppable(self.rules))

    @override
    def optimize(self) -> Generator[Optimizable]:
        dropped, self.rules = sift_optimizable(self.rules)
        yield from dropped

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

        return cls(
            match=match_class(*match_rule.args, **match_rule.kwargs),
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

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
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
