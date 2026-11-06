from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsRustProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a Rust project."""

    marker = "Cargo.toml"
