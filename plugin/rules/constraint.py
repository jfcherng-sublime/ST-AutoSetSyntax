import operator
import re
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Self
from typing import final
from typing import override

from more_itertools import first_true

from ..cache import clearable_lru_cache
from ..constants import PLUGIN_NAME
from ..constants import ST_PLATFORM
from ..logger import Logger
from ..snapshot import ViewSnapshot
from ..types import Optimizable
from ..types import StConstraintRule
from ..utils import camel_to_snake
from ..utils import compile_regex
from ..utils import drop_falsy
from ..utils import list_all_subclasses
from ..utils import merge_regexes
from ..utils import parse_regex_flags


def find_constraint(obj: Any) -> type[AbstractConstraint] | None:
    return first_true(get_constraints(), pred=lambda t: t.can_support(obj))


@clearable_lru_cache()
def get_constraints() -> tuple[type[AbstractConstraint], ...]:
    return tuple(sorted(list_constraints(), key=lambda cls: cls.name()))


def list_constraints() -> Generator[type[AbstractConstraint]]:
    yield from list_all_subclasses(AbstractConstraint, skip_abstract=True)  # type: ignore[type-abstract]


@dataclass(slots=True, frozen=True)
class ConstraintRule(Optimizable):
    constraint: AbstractConstraint | None = None
    constraint_name: str = ""
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    inverted: bool = False

    src_setting: StConstraintRule | None = None
    """The source setting object."""

    @override
    def is_droppable(self) -> bool:
        return not (self.constraint and not self.constraint.is_droppable())

    @override
    def droppable_value(self) -> bool:
        """
        A droppable constraint's underlying `AbstractConstraint.test()` always fails (`False`) --
        see `AbstractConstraint.is_droppable()`, whose contract is "droppable implies always
        fails". `inverted` flips that result, so a droppable *inverted* `ConstraintRule` is
        actually a constant `True`, not `False`.
        """
        return self.inverted

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

        Contract for subclasses: droppable must mean `test()` always fails (`False`), not always
        passes. Unlike `AbstractMatch`, constraints have no `droppable_value()` -- `ConstraintRule`
        assumes a droppable constraint is a constant `False` pre-inversion (see
        `ConstraintRule.droppable_value()`, which only flips that via `inverted`). A custom
        constraint whose `is_droppable()` reports `True` for a case where `test()` would actually
        return `True` breaks that assumption and will be pruned incorrectly.
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

    _COMPARATORS: ClassVar[dict[str, Callable[[Any, Any], bool]]] = {
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
    def _handled_comparator(comparator: str) -> Callable[[Any, Any], bool] | None:
        """Convert the comparator string into a callable."""
        return AbstractConstraint._COMPARATORS.get(comparator)

    @final
    @staticmethod
    def _handled_regex(args: tuple[Any, ...], kwargs: dict[str, Any]) -> re.Pattern[str]:
        """Returns compiled regex object from `args` and `kwargs.regex_flags`.

        ``drop_falsy`` is applied to ``args`` for consistency with ``_handled_args``:
        a falsy pattern like ``""`` or ``None`` in user settings would otherwise produce a
        surprising compiled regex: ``merge_regexes(("",))`` yields the empty group ``(?:)``
        (a zero-width match at every position, i.e. constant-True), and ``merge_regexes((None,))``
        yields ``(?:None)`` matching the literal string ``"None"``. Dropping falsy entries first
        makes these degenerate cases fall through to the "match nothing" sentinel instead.
        """
        # "regex_flags": null is present with value None, not absent, so .get(..., [...])'s
        # default doesn't cover it -- parse_regex_flags(None) would raise TypeError. Check for
        # None explicitly rather than falsy: "regex_flags": [] is a distinct, valid "no flags at
        # all, not even the usual MULTILINE" setting and must not be coerced into the default.
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

    @final
    def find_parent_with_sibling_cached(
        self,
        view_snapshot: ViewSnapshot,
        true_siblings: set[Path],
        sibling: str,
        *,
        use_exists: bool = False,
    ) -> bool:
        """Test whether the view's file is under a parent directory containing `sibling`, with caching."""
        if not (file_path_ := view_snapshot.file_path):
            raise AlwaysFalsyException("file not on disk")
        file_path = Path(file_path_)

        if first_true(file_path.parents, pred=lambda p: p in true_siblings):
            return True

        if found_sibling := self.find_parent_with_sibling(file_path, sibling, use_exists=use_exists):
            true_siblings.add(found_sibling)
            return True

        return False


class AlwaysValueException[T](Exception, ABC):
    """Used to indicate that the constraint returns a fixed value no matter it's inverted or not."""

    value: T


class AlwaysBoolException(AlwaysValueException[bool], ABC):
    pass


class AlwaysTruthyException(AlwaysBoolException):
    value = True


class AlwaysFalsyException(AlwaysBoolException):
    value = False
