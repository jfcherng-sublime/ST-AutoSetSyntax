from abc import ABC
from typing import Any
from typing import ClassVar
from typing import final

from ..utils import camel_to_snake


class NamedImplementation(ABC):
    """What a constraint and a match share: settings refer to either one by a name derived from its class."""

    _NAME_SUFFIX: ClassVar[str]
    """Dropped from the class name to get the name: `FooBarConstraint` is `foo_bar`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @final
    @classmethod
    def name(cls) -> str:
        """The name settings use for this class, derived from the class name."""
        return camel_to_snake(cls.__name__.removesuffix(cls._NAME_SUFFIX))

    @final
    @classmethod
    def can_support(cls, obj: Any) -> bool:
        """Determines whether this class supports `obj`."""
        return str(obj) == cls.name()
