from __future__ import annotations

# __future__ must be the first import
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, TypedDict, Union
import sublime


SyntaxLike = Union[str, sublime.Syntax]


class ListenerEvent(Enum):
    """
    Events used in AutoSetSyntax.
    """

    COMMAND = "command"
    EXEC = "exec"
    INIT = "init"
    LOAD = "load"
    MODIFY = "modify"
    NEW = "new"
    PASTE = "paste"
    RELOAD = "reload"
    REVERT = "revert"
    SAVE = "save"
    UNTRANSIENTIZE = "untransientize"

    def __str__(self) -> str:
        return str(self._value_)

    @classmethod
    def from_value(cls, value: Any) -> Optional[ListenerEvent]:
        try:
            return cls(value)
        except ValueError:
            return None


class Optimizable(metaclass=ABCMeta):
    def is_droppable(self) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def optimize(self) -> Generator[Any, None, None]:
        """Does optimizations and returns a generator for dropped objects."""
        ...


class ST_ConstraintRule(TypedDict):
    """Typed dict for corresponding ST settings"""

    constraint: str
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    inverted: bool


class ST_MatchRule(TypedDict):
    """Typed dict for corresponding ST settings"""

    match: str
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    rules: List[Union[ST_MatchRule, ST_ConstraintRule]]  # type: ignore


class ST_SyntaxRule(ST_MatchRule):
    """Typed dict for corresponding ST settings"""

    comment: str
    selector: str
    syntaxes: Union[str, List[str]]
    on_events: Optional[Union[str, List[str]]]


class TD_ViewSnapshot(TypedDict):
    id: int  # view ID
    char_count: int
    content: str  # pseudo file content
    file_name: str  # empty string if not on a disk
    file_path: str  # empty string if not on a disk
    file_size: int  # in bytes, -1 if file not on a disk
    first_line: str  # pseudo first line
    syntax: Optional[sublime.Syntax]  # note that the value is as-is when it's cached
