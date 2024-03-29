from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator, Union, final

from ..cache import clearable_lru_cache
from ..snapshot import ViewSnapshot
from ..types import Optimizable, ST_MatchRule
from ..utils import camel_to_snake, first_true, list_all_subclasses, remove_suffix
from .constraint import ConstraintRule


def find_match(obj: Any) -> type[AbstractMatch] | None:
    return first_true(get_matches(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_matches() -> tuple[type[AbstractMatch], ...]:
    return tuple(sorted(list_matches(), key=lambda cls: cls.name()))


def list_matches() -> Generator[type[AbstractMatch], None, None]:
    yield from list_all_subclasses(AbstractMatch, skip_abstract=True)  # type: ignore


@dataclass
class MatchRule(Optimizable):
    DEFAULT_MATCH_NAME = "any"

    match: AbstractMatch | None = None
    match_name: str = ""
    args: tuple[Any, ...] = tuple()
    kwargs: dict[str, Any] = field(default_factory=dict)
    rules: tuple[MatchableRule, ...] = tuple()

    def is_droppable(self) -> bool:
        return not (self.rules and self.match and not self.match.is_droppable(self.rules))

    def optimize(self) -> Generator[Optimizable, None, None]:
        rules: list[MatchableRule] = []
        for rule in self.rules:
            if rule.is_droppable():
                yield rule
                continue
            yield from rule.optimize()
            if rule.is_droppable():
                yield rule
                continue
            rules.append(rule)
        self.rules = tuple(rules)

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.match
        return self.match.test(view_snapshot, self.rules)

    @classmethod
    def make(cls, match_rule: ST_MatchRule) -> MatchRule:
        """Build this object with the `match_rule`."""
        obj = cls()

        if args := match_rule.get("args"):
            # make sure args is always a tuple
            obj.args = tuple(args) if isinstance(args, list) else (args,)

        if kwargs := match_rule.get("kwargs"):
            obj.kwargs = kwargs

        match = match_rule.get("match", cls.DEFAULT_MATCH_NAME)
        if match_class := find_match(match):
            obj.match_name = match
            obj.match = match_class(*obj.args, **obj.kwargs)

        rules_compiled: list[MatchableRule] = []
        for rule in match_rule.get("rules", []):
            rule_class: type[MatchableRule] | None = None
            if "constraint" in rule:
                rule_class = ConstraintRule
            elif "rules" in rule:  # nested MatchRule
                rule_class = MatchRule
            if rule_class and (rule_compiled := rule_class.make(rule)):  # type: ignore
                rules_compiled.append(rule_compiled)
        obj.rules = tuple(rules_compiled)

        return obj


# rules that can be used in a match rule
MatchableRule = Union[ConstraintRule, MatchRule]


class AbstractMatch(ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @final
    @classmethod
    def name(cls) -> str:
        """The nickname of this class. Converts "FooBarMatch" into "foo_bar" by default."""
        return camel_to_snake(remove_suffix(cls.__name__, "Match"))

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
                if goal == 0:
                    return True
            else:
                tolerance -= 1
        return False
