from typing import final

from ...constants import ST_PLATFORM
from ._fixed_value import AbstractFixedValueConstraint


@final
class IsPlatformConstraint(AbstractFixedValueConstraint):
    current = ST_PLATFORM
    noun = "platform"
