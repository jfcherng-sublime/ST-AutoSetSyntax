from __future__ import annotations

import operator
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self, final

from more_itertools import first_true

from ..cache import clearable_lru_cache
from ..constants import PLUGIN_NAME, ST_PLATFORM
from ..logger import Logger
from ..snapshot import ViewSnapshot
from ..types import Optimizable, StConstraintRule
from ..utils import camel_to_snake, compile_regex, drop_falsy, list_all_subclasses, merge_regexes, parse_regex_flags


def find_constraint(obj: Any) -> type[AbstractConstraint] | None:
    return first_true(get_constraints(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_constraints() -> tuple[type[AbstractConstraint], ...]:
    return tuple(sorted(list_constraints(), key=lambda cls: cls.name()))


def list_constraints() -> Generator[type[AbstractConstraint]]:
    yield from list_all_subclasses(AbstractConstraint, skip_abstract=True)  # type: ignore


@dataclass
class ConstraintRule(Optimizable):
    constraint: AbstractConstraint | None = None
    constraint_name: str = ""
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    inverted: bool = False

    src_setting: StConstraintRule | None = None
    """The source setting object."""

    def is_droppable(self) -> bool:
        return not (self.constraint and not self.constraint.is_droppable())

    def optimize(self) -> Generator[Optimizable]:
        return
        yield

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.constraint

        try:
            result = self.constraint.test(view_snapshot)
        except AlwaysBoolException as e:
            return e.value
        except Exception as e:
            print(f"[{PLUGIN_NAME}] ConstraintRule Exception: {e}")
            return False

        return not result if self.inverted else result

    @classmethod
    def make(cls, constraint_rule: StConstraintRule) -> Self | None:
        """Build this object with the `constraint_rule`."""
        constraint = constraint_rule.constraint
        if not (constraint_class := find_constraint(constraint)):
            Logger.log(f"❌ Unsupported constraint rule: {constraint}")
            return None

        return cls(
            constraint=constraint_class(*constraint_rule.args, **constraint_rule.kwargs),
            constraint_name=constraint,
            args=tuple(constraint_rule.args),
            kwargs=constraint_rule.kwargs,
            inverted=constraint_rule.inverted,
            src_setting=constraint_rule,
        )


class AbstractConstraint(ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @final
    @classmethod
    def name(cls) -> str:
        """The nickname of this class. Converts "FooBarConstraint" into "foo_bar" by default."""
        return camel_to_snake(cls.__name__.removesuffix("Constraint"))

    @final
    @classmethod
    def can_support(cls, obj: Any) -> bool:
        """Determines whether this class supports `obj`."""
        return str(obj) == cls.name()

    def is_droppable(self) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        """Tests whether the `view_snapshot` passes this constraint."""

    @final
    def _handled_args[T](self, normalizer: Callable[[T], T] | None = None) -> tuple[T, ...]:
        """Filter falsy args and normalize them. Note that `0`, `""` and `None` are falsy."""
        args: Iterable[T] = drop_falsy(self.args)
        if normalizer:
            args = map(normalizer, args)
        return tuple(args)

    @final
    @staticmethod
    def _handled_comparator(comparator: str) -> Callable[[Any, Any], bool] | None:
        """Convert the comparator string into a callable."""
        if comparator in {"<", "lt"}:
            return operator.lt
        if comparator in {"<=", "le", "lte"}:
            return operator.le
        if comparator in {">=", "ge", "gte"}:
            return operator.ge
        if comparator in {">", "gt"}:
            return operator.gt
        if comparator in {"=", "==", "===", "eq", "is"}:
            return operator.eq
        if comparator in {"!", "!=", "!==", "<>", "ne", "neq", "not"}:
            return operator.ne
        return None

    @final
    @staticmethod
    def _handled_regex(args: tuple[Any, ...], kwargs: dict[str, Any]) -> re.Pattern[str]:
        """Returns compiled regex object from `args` and `kwargs.regex_flags`."""
        return compile_regex(
            merge_regexes(args),
            parse_regex_flags(kwargs.get("regex_flags", ["MULTILINE"])),
        )

    @final
    @staticmethod
    def _handled_case_insensitive(kwargs: dict[str, Any]) -> bool:
        """Returns `case_insensitive` in `kwars`. Defaulted to platform's specification."""
        return bool(kwargs.get("case_insensitive", ST_PLATFORM in {"windows", "osx"}))

    @final
    @staticmethod
    def find_parent_with_sibling(base: str | Path, sibling: str, *, use_exists: bool = False) -> Path | None:
        """Find the first parent directory which contains `sibling`."""
        try:
            path = Path(base).resolve()
        except Exception:
            return None

        if use_exists:
            checker = Path.exists
        elif sibling.endswith(("\\", "/")):
            checker = Path.is_dir
        else:
            checker = Path.is_file

        return first_true(path.parents, pred=lambda p: checker(p / sibling))


class AlwaysValueException[T](Exception, ABC):
    """Used to indicate that the constraint returns a fixed value no matter it's inverted or not."""

    value: T


class AlwaysBoolException(AlwaysValueException[bool], ABC):
    pass


class AlwaysTruthyException(AlwaysBoolException):
    value = True


class AlwaysFalsyException(AlwaysBoolException):
    value = False
