from __future__ import annotations

# __future__ must be the first import
from ..constant import PLUGIN_NAME
from ..constant import ST_PLATFORM
from ..helper import camel_to_snake
from ..helper import compile_regex
from ..helper import first
from ..helper import get_all_subclasses
from ..helper import merge_regexes
from ..helper import parse_regex_flags
from ..helper import remove_suffix
from ..lru_cache import clearable_lru_cache
from ..snapshot import ViewSnapshot
from ..types import Optimizable, ST_ConstraintRule, TD_ViewSnapshot
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterable, Optional, Pattern, Tuple, Type, TypeVar, Union
import operator
import sublime

T = TypeVar("T")


def find_constraint(obj: Any) -> Optional[Type[AbstractConstraint]]:
    return first(get_constraints(), lambda t: t.is_supported(obj))


@clearable_lru_cache()
def get_constraints() -> Tuple[Type[AbstractConstraint], ...]:
    return tuple(
        sorted(
            get_all_subclasses(AbstractConstraint, skip_abstract=True),  # type: ignore
            key=lambda cls: cls.name(),
        )
    )


@dataclass
class ConstraintRule(Optimizable):
    constraint: Optional[AbstractConstraint] = None
    constraint_name: str = ""
    args: Tuple[Any, ...] = tuple()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    inverted: bool = False  # whether the test result should be inverted

    def is_droppable(self) -> bool:
        return not (self.constraint and not self.constraint.is_droppable())

    def optimize(self) -> Generator[Optimizable, None, None]:
        return
        yield

    def test(self, view: sublime.View) -> bool:
        assert self.constraint

        try:
            result = self.constraint.test(view)
        except AlwaysTruthyException:
            return True
        except AlwaysFalsyException:
            return False
        except Exception as e:
            print(f"[{PLUGIN_NAME}] ConstraintRule Exception: {e}")
            return False

        return not result if self.inverted else result

    @classmethod
    def make(cls, constraint_rule: ST_ConstraintRule) -> ConstraintRule:
        """Build this object with the `constraint_rule`."""
        obj = cls()

        if args := constraint_rule.get("args"):
            # make sure args is always a tuple
            obj.args = tuple(args) if isinstance(args, list) else (args,)

        if kwargs := constraint_rule.get("kwargs"):
            obj.kwargs = kwargs

        if (inverted := constraint_rule.get("inverted")) is not None:
            obj.inverted = bool(inverted)

        if constraint := constraint_rule.get("constraint"):
            obj.constraint_name = constraint
            if constraint_class := find_constraint(constraint):
                obj.constraint = constraint_class(*obj.args, **obj.kwargs)

        return obj


class AbstractConstraint(ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def name(cls) -> str:
        """The nickname of this class. Converts "FooBarConstraint" into "foo_bar" by default."""
        return camel_to_snake(remove_suffix(cls.__name__, "Constraint"))

    @classmethod
    def is_supported(cls, obj: Any) -> bool:
        """Determines whether this class supports `obj`."""
        return str(obj) == cls.name()

    def is_droppable(self) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def test(self, view: sublime.View) -> bool:
        """Tests whether the `view` passes this constraint."""
        ...

    def _handled_args(self, normalizer: Optional[Callable[[T], T]] = None) -> Tuple[T, ...]:
        """Filter falsy args and normalize them. Note that `0`, `""` and `None` are falsy."""
        args: Iterable[T] = filter(None, self.args)
        if normalizer:
            args = map(normalizer, args)
        return tuple(args)

    @staticmethod
    def _handled_comparator(comparator: str) -> Optional[Callable[[Any, Any], bool]]:
        """Convert the comparator string into a callable."""
        op: Optional[Callable[[Any, Any], bool]] = None
        if comparator in {"<", "lt"}:
            op = operator.lt
        elif comparator in {"<=", "le", "lte"}:
            op = operator.le
        elif comparator in {">=", "ge", "gte"}:
            op = operator.ge
        elif comparator in {">", "gt"}:
            op = operator.gt
        elif comparator in {"=", "==", "===", "eq"}:
            op = operator.eq
        elif comparator in {"!", "!=", "!==", "<>", "ne", "neq"}:
            op = operator.ne
        return op

    @staticmethod
    def _handled_regex(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Pattern[str]:
        """Returns compiled regex object from `args` and `kwargs.regex_flags`."""
        return compile_regex(
            merge_regexes(args),
            parse_regex_flags(kwargs.get("regex_flags", ["MULTILINE"])),
        )

    @staticmethod
    def _handled_case_insensitive(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> bool:
        """Returns compiled regex object from `args` and `kwargs.regex_flags`."""
        return bool(kwargs.get("case_insensitive", ST_PLATFORM in {"windows", "osx"}))

    @staticmethod
    def get_view_info(view: sublime.View) -> TD_ViewSnapshot:
        """Gets the cached information for the `view`."""
        snapshot = ViewSnapshot.get_by_view(view)
        assert snapshot  # our workflow guarantees this won't be None
        return snapshot

    @staticmethod
    def has_sibling(me: Union[str, Path], sibling: str, use_exists: bool = False) -> bool:
        if use_exists:
            checker = Path.exists
        else:
            checker = Path.is_dir if sibling.endswith(("\\", "/")) else Path.is_file

        folder_prev, folder = None, Path(me).resolve().parent
        while folder != folder_prev:
            if checker(folder / sibling):
                return True
            folder_prev, folder = folder, folder.parent
        return False


class AlwaysTruthyException(Exception):
    """Used to indicate that the constraint returns `True` no matter it's inverted or not."""

    ...


class AlwaysFalsyException(Exception):
    """Used to indicate that the constraint returns `False` no matter it's inverted or not."""

    ...
