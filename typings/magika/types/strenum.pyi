import enum

class StrEnum(str, enum.Enum):
    """
    StrEnum is a Python ``enum.Enum`` that inherits from ``str``. The default
    ``auto()`` behavior uses the lower-case version of the name. This is meant
    to reflect the behavior of `enum.StrEnum`, available from Python 3.11.
    """
    def __new__(cls, value: str | StrEnum, *args, **kwargs): ...
    def __str__(self) -> str: ...
    def _generate_next_value_(name, *_): ...

class LowerCaseStrEnum(StrEnum):
    def _generate_next_value_(name, *_): ...
