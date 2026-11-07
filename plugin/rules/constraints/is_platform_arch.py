from typing import final

from ...constants import ST_PLATFORM_ARCH
from ._fixed_value import AbstractFixedValueConstraint


@final
class IsPlatformArchConstraint(AbstractFixedValueConstraint):
    current = ST_PLATFORM_ARCH
    args_noun = "platform/arch pair"
