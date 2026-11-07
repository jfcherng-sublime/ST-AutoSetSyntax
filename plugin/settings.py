from collections import ChainMap
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import MutableMapping
from itertools import chain
from typing import Any
from typing import ClassVar
from typing import Final

import sublime
from more_itertools import unique_everseen
from pydantic import ValidationError

from .constants import PLUGIN_NAME
from .types import RULE_KIND_TAGS
from .types import DroppedRule
from .types import StSyntaxRule
from .types import WindowId
from .utils import drop_falsy

type SettingsDict = MutableMapping[str, Any]
type MergedSettingsDict = Mapping[str, Any]


def get_merged_plugin_setting(key: str, default: Any | None = None, *, window: sublime.Window) -> Any:
    return get_merged_plugin_settings(window=window).get(key, default)


def get_merged_plugin_settings(*, window: sublime.Window) -> MergedSettingsDict:
    return AioSettings.get_all(window)


def get_st_setting(key: str, default: Any | None = None) -> Any:
    # Preferences are not layered through `AioSettings`, which is what drops explicit nulls
    value = get_st_settings().get(key, default)
    return default if value is None else value


def get_st_settings() -> sublime.Settings:
    return sublime.load_settings("Preferences.sublime-settings")


SYNTAX_RULE_SOURCES: Final = ("core_syntax_rules", "project_syntax_rules", "user_syntax_rules", "default_syntax_rules")
"""The settings syntax rules come from, in the order they're tested (the first matching rule wins)."""


def pref_syntax_rules(*, window: sublime.Window) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
    """
    The syntax rules, validated one by one, plus the ones that failed, located for the user.

    A malformed rule must cost only itself: validating all of them as one list failed on the first
    typo and threw away every rule, the bundled ones included.
    """
    settings = get_merged_plugin_settings(window=window)
    valid: list[StSyntaxRule] = []
    invalid: list[DroppedRule] = []
    for source in SYNTAX_RULE_SOURCES:
        if (rules := settings.get(source)) is None:  # an explicit `null` means "unset", like absent
            continue
        if not isinstance(rules, list):
            invalid.append(DroppedRule.invalid(source, rules, f"expected a list of rules, got {type(rules).__name__}"))
            continue
        for index, rule in enumerate(rules):
            try:
                valid.append(StSyntaxRule.model_validate(rule))
            except ValidationError as e:
                invalid.append(DroppedRule.invalid(f"{source}[{index}]", rule, _describe_validation_error(e)))
    return valid, invalid


def _describe_validation_error(e: ValidationError) -> str:
    """One `where: what` per problem (e.g. `rules[0].args: ...`), on one line, instead of pydantic's report."""

    def where(loc: tuple[int | str, ...]) -> str:
        # drop the rule-kind tags pydantic inserts: they name a model, not anything in the user's settings
        parts = (part for part in loc if part not in RULE_KIND_TAGS)
        return "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts).lstrip(".")

    return "; ".join(
        f"{location}: {error['msg']}" if (location := where(error["loc"])) else error["msg"]
        for error in e.errors(include_url=False)
    )


def _as_list(value: Any) -> list[Any]:
    """Coerces a settings value to a list; anything else, including an absent key, is no list at all."""
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerces a settings value to a dict; anything else, including `null`, is no dict at all."""
    return value if isinstance(value, dict) else {}


def _drop_nulls(settings: Mapping[str, Any]) -> dict[str, Any]:
    """
    Treat an explicit `null` as "not configured", so that it falls through to the next layer
    (or the reader's default) instead of reaching a reader as `None` -- `.get(key, default)`
    only applies its default to an absent key, not a `null` one.
    """
    return {key: value for key, value in settings.items() if value is not None}


def _derive_settings(settings: MergedSettingsDict) -> dict[str, Any]:
    ret: dict[str, Any] = {}

    # syntax rules aren't merged here: `pref_syntax_rules()` validates each source separately, so
    # a malformed rule can be reported with where it came from

    # use tuple to freeze setting for better performance (cache-able)
    ret["trim_suffixes"] = tuple(
        drop_falsy(
            unique_everseen(
                chain(
                    _as_list(settings.get("project_trim_suffixes")),
                    _as_list(settings.get("user_trim_suffixes")),
                    _as_list(settings.get("default_trim_suffixes")),
                ),
            ),
        ),
    )

    return ret


class AioSettings:
    """
    All-in-one settings for the plugin.

    This class provides merged settings of plugin settings and project settings.
    """

    _on_change: ClassVar[Callable[[sublime.Window], None] | None] = None
    _plugin_settings_object: ClassVar[sublime.Settings | None] = None

    # application-level
    _plugin_settings: ClassVar[SettingsDict] = {}

    # window-level; a window is tracked exactly when it has merged settings
    _project_plugin_settings: ClassVar[dict[WindowId, SettingsDict]] = {}
    _merged_plugin_settings: ClassVar[dict[WindowId, MergedSettingsDict]] = {}

    @classmethod
    def set_up(cls, on_change: Callable[[sublime.Window], None]) -> None:
        """
        Load the settings of every window. `on_change` is called with a window whose settings
        change afterwards, not for this initial load.
        """
        cls._plugin_settings_object = sublime.load_settings(f"{PLUGIN_NAME}.sublime-settings")
        cls._plugin_settings_object.add_on_change(cls.__name__, cls._on_plugin_settings_change)
        cls._update_plugin_settings()
        for window in sublime.windows():
            cls.track(window)
        cls._on_change = on_change

    @classmethod
    def tear_down(cls) -> None:
        if cls._plugin_settings_object is not None:
            cls._plugin_settings_object.clear_on_change(cls.__name__)
            cls._plugin_settings_object = None
        cls._on_change = None
        cls._plugin_settings.clear()
        cls._project_plugin_settings.clear()
        cls._merged_plugin_settings.clear()

    @classmethod
    def get_all(cls, window: sublime.Window) -> MergedSettingsDict:
        return cls._merged_plugin_settings.get(window.id()) or {}

    @classmethod
    def track(cls, window: sublime.Window) -> None:
        """(Re)read the window's project settings and merge them, without telling anyone."""
        window_id = window.id()
        project_settings = _as_dict((window.project_data() or {}).get("settings"))
        cls._project_plugin_settings[window_id] = {"__comment": "project_settings"} | _drop_nulls(
            _as_dict(project_settings.get(PLUGIN_NAME))
        )

        merged = ChainMap(cls._project_plugin_settings[window_id], cls._plugin_settings)
        produced = {"__comment": "produced_settings"} | _derive_settings(merged)
        cls._merged_plugin_settings[window_id] = ChainMap(produced, *merged.maps)

    @classmethod
    def forget(cls, window: sublime.Window) -> None:
        window_id = window.id()
        cls._merged_plugin_settings.pop(window_id, None)
        cls._project_plugin_settings.pop(window_id, None)

    @classmethod
    def refresh(cls, window: sublime.Window) -> None:
        """The window's settings may have changed: re-merge them and tell `on_change`."""
        cls.track(window)
        if cls._on_change:
            cls._on_change(window)

    @classmethod
    def _on_plugin_settings_change(cls) -> None:
        cls._update_plugin_settings()
        for window in sublime.windows():
            cls.refresh(window)

    @classmethod
    def _update_plugin_settings(cls) -> None:
        assert cls._plugin_settings_object
        cls._plugin_settings = {"__comment": "plugin_settings"} | _drop_nulls(cls._plugin_settings_object.to_dict())
