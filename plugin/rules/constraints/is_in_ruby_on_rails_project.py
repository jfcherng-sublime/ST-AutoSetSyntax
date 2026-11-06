from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsInRubyOnRailsProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    marker = "config/routes.rb"
