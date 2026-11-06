import operator
import re
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Self
from typing import final
from typing import override

from more_itertools import first_true

from ..cache import clearable_lru_cache
from ..constants import PLUGIN_NAME
from ..constants import ST_PLATFORM
from ..logger import Logger
from ..snapshot import ViewSnapshot
from ..types import UNFOLDED
from ..types import Fold
from ..types import Optimizable
from ..types import StConstraintRule
from ..utils import compile_regex
from ..utils import drop_falsy
from ..utils import list_all_subclasses
from ..utils import merge_regexes
from ..utils import parse_regex_flags
from ._named import NamedImplementation
from ._optimize import require_fold


def find_constraint(obj: Any) -> type[AbstractConstraint] | None:
    """Find a constraint class that supports `obj`."""
    return first_true(get_constraints(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_constraints() -> tuple[type[AbstractConstraint], ...]:
    implementations = list_all_subclasses(AbstractConstraint, skip_abstract=True)  # type: ignore[type-abstract]
    return tuple(sorted(implementations, key=lambda cls: cls.name()))


@dataclass(slots=True, frozen=True)
class ConstraintRule(Optimizable):
    constraint: AbstractConstraint | None = None
    constraint_name: str = ""
    inverted: bool = False

    src_setting: StConstraintRule | None = None
    """The source setting object."""

    @override
    def fold(self) -> Fold:
        # `make()` returns `None` rather than a constraint-less rule, and every parent drops
        # those, so a rule in a compiled tree always has one -- same assumption `test()` makes
        assert self.constraint

        value, reason = require_fold(self.constraint, self.constraint.fold())
        if value is None:
            return UNFOLDED
        if not self.inverted:
            return Fold(value, reason)
        # the reason states what the *constraint* settled, so say "not" flipped it, or the
        # report reads "always matches: no extension was given"
        return Fold(not value, ", ".join(drop_falsy((reason, 'negated by "not"'))))

    @override
    def optimize(self) -> Generator[Optimizable]:
        """Leaf constraint has no sub-rules to optimize."""
        yield from ()

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.constraint

        try:
            result = self.constraint.test(view_snapshot)
        except AlwaysBoolException as e:
            return e.value
        except Exception as e:
            Logger.log(f"[{PLUGIN_NAME}] ConstraintRule Exception: {e}")
            return False

        return not result if self.inverted else result

    @classmethod
    def make(cls, constraint_rule: StConstraintRule) -> Self | None:
        """Build this object with the `constraint_rule`."""
        constraint = constraint_rule.constraint
        if not (constraint_class := find_constraint(constraint)):
            Logger.log(f"❌ Unsupported constraint rule: {constraint}")
            return None

        try:
            constraint_obj = constraint_class(*constraint_rule.args, **constraint_rule.kwargs)
        except Exception as e:
            Logger.log(
                f"❌ Failed to create constraint {constraint}({constraint_rule.args}, {constraint_rule.kwargs}): {e}"
            )
            return None

        return cls(
            constraint=constraint_obj,
            constraint_name=constraint,
            inverted=constraint_rule.inverted,
            src_setting=constraint_rule,
        )


class AbstractConstraint(NamedImplementation):
    _NAME_SUFFIX = "Constraint"

    def fold(self) -> Fold:
        """
        The constant `test()` always returns and why, or `UNFOLDED` when the result still
        depends on the view.

        Override this when this constraint's own arguments already settle the answer: e.g.
        `is_extension` with no extensions given can never match, so it folds to
        `Fold(False, "no extensions given")`, and `contains` with a threshold of `0` always
        matches, so it folds to `Fold(True, ...)`. A folded constraint is reported to the user as
        a dropped rule -- carrying that reason verbatim -- instead of being tested per view.
        """
        return UNFOLDED

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

    _COMPARATORS: Final[ClassVar[dict[str, Callable[[Any, Any], bool]]]] = {
        "<": operator.lt,
        "lt": operator.lt,
        # ...
        "<=": operator.le,
        "le": operator.le,
        "lte": operator.le,
        # ...
        ">=": operator.ge,
        "ge": operator.ge,
        "gte": operator.ge,
        # ...
        ">": operator.gt,
        "gt": operator.gt,
        # ...
        "=": operator.eq,
        "==": operator.eq,
        "===": operator.eq,
        "eq": operator.eq,
        "is": operator.eq,
        # ...
        "!": operator.ne,
        "!=": operator.ne,
        "!==": operator.ne,
        "<>": operator.ne,
        "ne": operator.ne,
        "neq": operator.ne,
        "not": operator.ne,
    }

    @final
    @staticmethod
    def _handled_comparison(args: tuple[Any, ...]) -> tuple[Callable[[Any, Any], bool], float]:
        """
        Parse `args` as `(comparator, threshold)`.

        Raise rather than fold to `False`: a typo'd comparator under `"not"` would fold to `True`,
        i.e. a typo made the rule match every file. Raising makes the whole rule invalid instead.
        """
        if len(args) != 2:
            raise ValueError(f"expects exactly 2 args (a comparator and a threshold), got {len(args)}")
        comparator, threshold = args
        if not (comparator_func := AbstractConstraint._COMPARATORS.get(comparator)):
            raise ValueError(f"{comparator!r} is not a known comparator")
        return comparator_func, float(threshold)

    @final
    @staticmethod
    def _handled_threshold(kwargs: dict[str, Any]) -> int:
        """
        The `threshold` in `kwargs`, an integer count of matches. Defaulted to `1`.

        Raise rather than fold to `False`, for the same reason as `_handled_comparison()`.
        """
        threshold = kwargs.get("threshold", 1)
        # `bool` is an `int` subclass, but `true` in settings is surely not meant as a count of 1
        if not isinstance(threshold, int) or isinstance(threshold, bool):
            raise ValueError(f'"threshold" must be an integer, got {threshold!r}')
        return threshold

    @final
    @staticmethod
    def _handled_regex(args: tuple[Any, ...], kwargs: dict[str, Any]) -> re.Pattern[str]:
        """
        Returns compiled regex object from `args` and `kwargs.regex_flags`.

        Falsy patterns are dropped first, as in `_handled_args()`: `""` would otherwise compile
        to a regex matching everywhere and `None` to one matching the text "None".
        """
        # `[]` is a real value (no flags, not even MULTILINE), so only `None` means "use the default"
        regex_flags = kwargs.get("regex_flags")
        return compile_regex(
            merge_regexes(drop_falsy(args)),
            parse_regex_flags(regex_flags if regex_flags is not None else ["MULTILINE"]),
        )

    @final
    @staticmethod
    def _handled_case_insensitive(kwargs: dict[str, Any]) -> bool:
        """Returns `case_insensitive` in `kwars`. Defaulted to platform's specification."""
        return bool(kwargs.get("case_insensitive", ST_PLATFORM in {"windows", "osx"}))


class AlwaysValueException[T](Exception, ABC):
    """Used to indicate that the constraint returns a fixed value no matter it's inverted or not."""

    value: T


class AlwaysBoolException(AlwaysValueException[bool], ABC):
    pass


class AlwaysTruthyException(AlwaysBoolException):
    value = True


class AlwaysFalsyException(AlwaysBoolException):
    value = False
