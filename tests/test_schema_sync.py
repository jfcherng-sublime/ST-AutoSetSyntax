"""The settings schema names constraints, matches and events by hand; these catch it drifting from the code."""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from plugin.rules import get_constraints
from plugin.rules import get_matches
from plugin.types import ListenerEvent

_SCHEMA = json.loads(
    re.sub(
        r"^\s*//.*$",
        "",
        (Path(__file__).parent.parent / "sublime-package.json").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
)


def _find(node: Any, key: str) -> Iterator[Any]:
    """Every value under `key`, anywhere in the schema."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from _find(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _find(item, key)


def _definitions() -> dict[str, Any]:
    return next(_find(_SCHEMA, "definitions"))


def test_constraint_enum_lists_every_constraint():
    prop = _definitions()["constraint_rule"]["properties"]["constraint"]
    assert prop["enum"] == [cls.name() for cls in get_constraints()]


def test_every_constraint_has_a_description():
    prop = _definitions()["constraint_rule"]["properties"]["constraint"]
    assert len(prop["markdownEnumDescriptions"]) == len(prop["enum"])


def test_match_enum_lists_every_match():
    prop = _definitions()["match_rule"]["properties"]["match"]
    assert sorted(prop["enum"]) == [cls.name() for cls in get_matches()]


def test_on_events_enum_lists_every_event():
    for events in _find(_SCHEMA, "on_events"):
        assert events["items"]["enum"] == [event.value for event in ListenerEvent]
