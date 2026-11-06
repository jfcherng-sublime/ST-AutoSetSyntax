from typing import final

from ...constants import ST_ARCH
from ._fixed_value import AbstractFixedValueConstraint


@final
class IsArchConstraint(AbstractFixedValueConstraint):
    current = ST_ARCH
    noun = "architecture"
