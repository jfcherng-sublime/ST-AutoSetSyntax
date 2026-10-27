"""
Syntax rules shipped by other packages, each in one file at its package root.

A package that knows its own file format better than any generic heuristic does can drop an
`AutoSetSyntax.rules.sublime-settings` file in its root and have those rules picked up, instead of
maintaining a small plugin whose only job is "set my syntax when a file looks like mine".

The file is deliberately not read with `sublime.load_settings()`: that merges every package's file
of the same name into one object and throws away which package a rule came from, and "this rule came
from Packages/Foo/" is the whole point -- it's what makes a bad package diagnosable. The per-file
read below keeps each rule's origin in the location string of its dropped entries.
"""

from collections.abc import Callable
from collections.abc import Collection
from typing import Any
from typing import Final

import sublime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from .constants import PLUGIN_NAME
from .types import DroppedRule
from .types import StSyntaxRule
from .types import describe_validation_error

RULES_RESOURCE_NAME: Final = "AutoSetSyntax.rules.sublime-settings"
"""The file a package puts its syntax rules in. Matched by file name, so any directory works."""

_EXCLUDED_PACKAGES: Final = ("User",)
"""Packages to ignore beyond our own.

A copy of a rules file in `Packages/User/` would sit at a *lower* priority than the
`user_syntax_rules` it duplicates, which is the opposite of what someone copying it there expects,
so the file would look like it does nothing.
"""

type EnvelopeParser = Callable[..., tuple[list[StSyntaxRule], list[DroppedRule]]]
"""Parses one spec version's envelope into rules, given `(data, *, location)`."""


class _EnvelopeV1(BaseModel):
    """The v1 envelope: `{"spec_version": 1, "rules": [...]}`."""

    # a typo'd top-level key ("rule" for "rules") must not silently contribute nothing: the only
    # keys a v1 file may have are the version and the rules themselves
    model_config = ConfigDict(extra="forbid")

    # `strict` rejects `True`, `"1"` and `1.0`, which pydantic would otherwise coerce to 1. The
    # version decides whether the rest of the file is read at all, so it's worth being pedantic: a
    # file whose version is wrong contributes nothing and deserves to say so.
    spec_version: int = Field(strict=True)
    """The rules-file spec version the file was written against."""

    rules: list[Any]
    """The rules, as written.

    Deliberately untyped: validating the whole list as `list[StSyntaxRule]` would fail as a unit, so
    one typo would cost the package every rule it ships (see `pref_syntax_rules()`, which validates
    one rule at a time for exactly this reason). Validated entry by entry in `_parse_v1()`."""

    schema_: Any = Field(default=None, alias="$schema")
    """Allowed and ignored, so editors outside Sublime Text can validate the file."""


def _parse_v1(data: Any, *, location: str) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
    """Parse a v1 envelope into rules. Only ever called with a dict whose `spec_version` is 1."""
    try:
        envelope = _EnvelopeV1.model_validate(data)
    except ValidationError as e:
        return [], [DroppedRule.invalid(location, data, describe_validation_error(e))]

    rules: list[StSyntaxRule] = []
    invalid: list[DroppedRule] = []
    for index, rule in enumerate(envelope.rules):
        try:
            rules.append(StSyntaxRule.model_validate(rule))
        except ValidationError as e:
            invalid.append(DroppedRule.invalid(f"{location}[{index}]", rule, describe_validation_error(e)))
    return rules, invalid


# The seam for a future spec version: a v2 file gets its own envelope model and parse function and
# one more line here, and every v1 file already in the wild keeps parsing through `_parse_v1()`.
# Nothing else in the plugin knows which version produced its rules.
_ENVELOPE_PARSERS: Final[dict[int, EnvelopeParser]] = {1: _parse_v1}

SPEC_VERSION: Final = max(_ENVELOPE_PARSERS)
"""The newest rules-file spec version this plugin implements.

The rule vocabulary -- constraint and match names, their arguments -- is *not* versioned by this
number: it only ever grows and the schema only ever loosens, so a file that spells out its rules in
full keeps working across plugin versions. Only the envelope around the rules is versioned, because
that's the part an older plugin cannot read at all.
"""


def _is_excluded(resource: str) -> bool:
    """Whether `resource` belongs to one of our own packages rather than a third party's.

    `PLUGIN_NAME` is read here rather than copied into a tuple at import time only so that tests,
    which import this module under a different package name, can point it at the real one.
    """
    return resource.startswith(tuple(f"Packages/{name}/" for name in (PLUGIN_NAME, *_EXCLUDED_PACKAGES)))


def parse_package_rules(data: Any, *, location: str) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
    """
    Validate one package's rules file, naming it `location` in any complaint.

    Never raises: anything wrong with the file becomes a dropped entry instead, so that one bad file
    cannot cost the user the rules of every other package.
    """
    if not isinstance(data, dict):
        return [], [DroppedRule.invalid(location, data, f"expected an object, got {type(data).__name__}")]

    # The version gate has to come before the envelope is validated rather than as one of its rules.
    # A file written against a newer spec has keys the parser it would be handed forbids, and a pile
    # of "extra inputs are not permitted" for vocabulary this plugin doesn't have yet would bury the
    # one sentence that explains what's actually going on.
    version = data.get("spec_version")
    if isinstance(version, bool) or not isinstance(version, int):
        return [], [DroppedRule.invalid(location, data, 'it has no integer "spec_version"')]
    if version < 1:
        return [], [DroppedRule.invalid(location, data, f'"spec_version" {version} is not a spec version')]
    if (parse := _ENVELOPE_PARSERS.get(version)) is None:
        return [], [
            DroppedRule(
                f"ignored {location}: it declares spec_version {version}, but this version of the plugin "
                f"implements at most {SPEC_VERSION} -- update the plugin to use it",
                data,
            ),
        ]

    return parse(data, location=location)


def find_package_rules_resources(*, disabled_packages: Collection[str] = ()) -> list[str]:
    """Every package's rules file, sorted so that the same set of packages always behaves the same."""
    disabled = frozenset(disabled_packages)
    return sorted(
        path
        for path in sublime.find_resources(RULES_RESOURCE_NAME)
        if not _is_excluded(path) and _package_name(path) not in disabled
    )


def _package_name(resource: str) -> str:
    """The package a resource path belongs to: `Packages/Foo/bar.json` -> `Foo`."""
    _, _, package, *_ = resource.split("/")
    return package


def load_package_rules(
    *, disabled_packages: Collection[str] = ()
) -> tuple[list[tuple[StSyntaxRule, str]], list[DroppedRule]]:
    """
    Read and validate every package's rules file, in package order.

    The counterpart of `pref_syntax_rules()` for rules that live outside any settings object. Each
    rule is paired with the resource it came from, so a misbehaving rule can be traced to the
    package that ships it -- and then to `disabled_package_syntax_rule_packages`.
    """
    rules: list[tuple[StSyntaxRule, str]] = []
    dropped: list[DroppedRule] = []
    for location in find_package_rules_resources(disabled_packages=disabled_packages):
        try:
            # `decode_value()` reads the same JSON dialect as a `.sublime-settings` file (comments,
            # trailing commas), which is what the file name promises the author
            data = sublime.decode_value(sublime.load_resource(location))
        except Exception as e:  # a broken file, or one this process cannot read
            dropped.append(DroppedRule.invalid(location, None, f"cannot be read: {e}"))
            continue
        file_rules, file_dropped = parse_package_rules(data, location=location)
        rules.extend((rule, location) for rule in file_rules)
        dropped.extend(file_dropped)
    return rules, dropped
