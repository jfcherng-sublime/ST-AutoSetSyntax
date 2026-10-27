"""
Syntax rules shipped by other packages, each in one file at its package root.

A package that knows its own file format better than any generic heuristic does can drop an
`AutoSetSyntax.rules.v1.sublime-settings` file in its root and have those rules picked up, instead
of maintaining a small plugin whose only job is "set my syntax when a file looks like mine".

The format version lives in the *file name*, not in the file: `v1` above. That makes the version
visible to `find_resources()` before anything is read, so a file written against a format this
plugin doesn't implement is identified without guessing at its contents -- and it lets one package
ship several versions at once, so a file for a newer plugin doesn't break an older one.

The file is deliberately not read with `sublime.load_settings()`: that merges every package's file
of the same name into one object and throws away which package a rule came from, and "this rule came
from Packages/Foo/" is the whole point -- it's what makes a bad package diagnosable. The per-file
read below keeps each rule's origin in the location string of its dropped entries.
"""

import re
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

RULES_RESOURCE_GLOB: Final = "AutoSetSyntax.rules.v*.sublime-settings"
"""What `find_resources()` is asked for, so that every version -- including ones this plugin is too
old to read -- is found and can be explained, rather than silently ignored."""

_RE_RULES_RESOURCE: Final = re.compile(r"/AutoSetSyntax\.rules\.v(?P<version>[0-9]+)\.sublime-settings$")
"""Picks the version back out of a path the glob above matched."""

_EXCLUDED_PACKAGES: Final = ("User",)
"""Packages to ignore beyond our own.

A copy of a rules file in `Packages/User/` would sit at a *lower* priority than the
`user_syntax_rules` it duplicates, which is the opposite of what someone copying it there expects,
so the file would look like it does nothing.
"""

type EnvelopeParser = Callable[..., tuple[list[StSyntaxRule], list[DroppedRule]]]
"""Parses one format version's envelope into rules, given `(data, *, location)`."""


def rules_resource_name(version: int) -> str:
    """The file name a package ships its rules for `version` under."""
    return f"AutoSetSyntax.rules.v{version}.sublime-settings"


class _EnvelopeV1(BaseModel):
    """The v1 envelope: `{"rules": [...]}`. The version is in the file name, not in here."""

    # a typo'd top-level key ("rule" for "rules") must not silently contribute nothing: the only
    # other key a v1 file may have is the schema hint below
    model_config = ConfigDict(extra="forbid")

    rules: list[Any]
    """The rules, as written.

    Deliberately untyped: validating the whole list as `list[StSyntaxRule]` would fail as a unit, so
    one typo would cost the package every rule it ships (see `pref_syntax_rules()`, which validates
    one rule at a time for exactly this reason). Validated entry by entry in `_parse_v1()`."""

    schema_: Any = Field(default=None, alias="$schema")
    """Allowed and ignored, so editors outside Sublime Text can validate the file."""


def _parse_v1(data: Any, *, location: str) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
    """Parse a v1 envelope into rules. Only ever called for a file named `...rules.v1...`."""
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


# The seam for a future format: a v2 file gets its own envelope model and parse function and one
# more line here, and every v1 file already in the wild keeps parsing through `_parse_v1()`.
# Nothing else in the plugin knows which version produced its rules.
_ENVELOPE_PARSERS: Final[dict[int, EnvelopeParser]] = {1: _parse_v1}

SPEC_VERSION: Final = max(_ENVELOPE_PARSERS)
"""The newest rules format this plugin implements.

The rule vocabulary -- constraint and match names, their arguments -- is *not* versioned by this
number: it only ever grows and the schema only ever loosens, so a file that spells out its rules in
full keeps working across plugin versions. Only the envelope around the rules is versioned, because
that's the part an older plugin cannot read at all.
"""


def _package_name(resource: str) -> str:
    """The package a resource path belongs to: `Packages/Foo/bar.json` -> `Foo`."""
    return resource.split("/")[1]


def _is_excluded(resource: str) -> bool:
    """Whether `resource` belongs to one of our own packages rather than a third party's.

    `PLUGIN_NAME` is read here rather than copied into a tuple at import time only so that tests,
    which import this module under a different package name, can point it at the real one.
    """
    return resource.startswith(tuple(f"Packages/{name}/" for name in (PLUGIN_NAME, *_EXCLUDED_PACKAGES)))


def parse_package_rules(data: Any, *, location: str, version: int) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
    """
    Validate one package's rules file, written against format `version`, naming it `location`.

    Never raises: anything wrong with the file becomes a dropped entry instead, so that one bad file
    cannot cost the user the rules of every other package.
    """
    if not isinstance(data, dict):
        return [], [DroppedRule.invalid(location, data, f"expected an object, got {type(data).__name__}")]

    if (parse := _ENVELOPE_PARSERS.get(version)) is None:
        # unreachable through `load_package_rules()`, which only ever passes a supported version;
        # kept so that a future caller can't silently get a half-parsed file
        return [], [
            DroppedRule(f"ignored {location}: this version of the plugin cannot read the v{version} format", data),
        ]

    return parse(data, location=location)


def find_package_rules_resources(*, disabled_packages: Collection[str] = ()) -> dict[str, dict[int, str]]:
    """
    Every package's rules files as `{package: {version: resource path}}`, packages in sorted order.

    Grouped rather than flattened because the versions of one package compete: a package may ship
    several so that both an old and a new AutoSetSyntax read what they understand, and only one of
    them may be used, or the same rules would be applied twice.
    """
    disabled = frozenset(disabled_packages)
    found: dict[str, dict[int, str]] = {}
    for path in sorted(sublime.find_resources(RULES_RESOURCE_GLOB)):
        if _is_excluded(path) or _package_name(path) in disabled:
            continue
        if (match := _RE_RULES_RESOURCE.search(path)) is None:
            continue  # the glob matched something that isn't quite this shape
        found.setdefault(_package_name(path), {})[int(match["version"])] = path
    return dict(sorted(found.items()))


def load_package_rules(
    *, disabled_packages: Collection[str] = ()
) -> tuple[list[tuple[StSyntaxRule, str]], list[DroppedRule]]:
    """
    Read and validate the rules of every package, in package order.

    The counterpart of `pref_syntax_rules()` for rules that live outside any settings object. Each
    rule is paired with the resource it came from, so a misbehaving rule can be traced to the
    package that ships it -- and then to `disabled_package_syntax_rule_packages`.
    """
    rules: list[tuple[StSyntaxRule, str]] = []
    dropped: list[DroppedRule] = []

    for versions in find_package_rules_resources(disabled_packages=disabled_packages).values():
        if not (supported := sorted(set(versions) & set(_ENVELOPE_PARSERS))):
            # nothing readable: say which file was too new instead of ignoring the package entirely
            newest = max(versions)
            location = versions[newest]
            dropped.append(
                DroppedRule(
                    f"ignored {location}: it is written for the v{newest} rules format, but this version "
                    f"of the plugin implements at most v{SPEC_VERSION} -- update the plugin to use it",
                    None,
                    origin=location,
                )
            )
            continue

        # only the newest the plugin understands: a package shipping v1 and v2 wants one of them read,
        # not both, and `max(supported)` is the one written most recently
        location = versions[max(supported)]
        if stale := sorted(set(versions) - set(supported), reverse=True):
            dropped.append(
                DroppedRule(
                    f"ignored {versions[stale[0]]}: {location} is used for this package instead, because this "
                    f"version of the plugin implements at most v{SPEC_VERSION}",
                    None,
                    origin=versions[stale[0]],
                )
            )

        try:
            # `decode_value()` reads the same JSON dialect as a `.sublime-settings` file (comments,
            # trailing commas), which is what the file name promises the author
            data = sublime.decode_value(sublime.load_resource(location))
        except Exception as e:  # a broken file, or one this process cannot read
            dropped.append(DroppedRule.invalid(location, None, f"cannot be read: {e}"))
            continue

        file_rules, file_dropped = parse_package_rules(data, location=location, version=max(supported))
        rules.extend((rule, location) for rule in file_rules)
        dropped.extend(file_dropped)

    return rules, dropped
