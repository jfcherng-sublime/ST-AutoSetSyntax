from __future__ import annotations

# __future__ must be the first import
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, TypedDict, Union
import sublime


SyntaxLike = Union[str, sublime.Syntax]


class ListenerEvent(Enum):
    """Events used in AutoSetSyntax."""

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


class Optimizable(ABC):
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
    """Typed dict for corresponding ST settings."""

    constraint: str
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    inverted: bool


class ST_MatchRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    match: str
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    rules: List[Union[ST_MatchRule, ST_ConstraintRule]]  # type: ignore


class ST_SyntaxRule(ST_MatchRule):
    """Typed dict for corresponding ST settings."""

    comment: str
    selector: str
    syntaxes: Union[str, List[str]]
    on_events: Optional[Union[str, List[str]]]


class TD_ViewSnapshot(TypedDict):
    id: int
    """View ID."""
    char_count: int
    """Character count."""
    content: str
    """Pseudo file content."""
    file_name: str
    """The file name. Empty string if not on a disk."""
    file_name_unhidden: str
    """The file name without prefixed dots. Empty string if not on a disk."""
    file_path: str
    """Empty string if not on a disk."""
    file_size: int
    """In bytes, -1 if file not on a disk."""
    first_line: str
    """Pseudo first line."""
    syntax: Optional[sublime.Syntax]
    """Note that the value is as-is when it's cached."""
