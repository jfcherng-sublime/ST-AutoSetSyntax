from collections import ChainMap
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import MutableMapping
from itertools import chain
from typing import Any
from typing import ClassVar
from typing import Final

import sublime
import sublime_plugin
from more_itertools import unique_everseen
from pydantic import ValidationError

from .types import RULE_KIND_TAGS
from .types import DroppedRule
from .types import StSyntaxRule
from .types import WindowId
from .utils import drop_falsy

type SettingsDict = MutableMapping[str, Any]
type MergedSettingsDict = Mapping[str, Any]


def get_merged_plugin_setting(
    key: str,
    default: Any | None = None,
    *,
    window: sublime.Window | None = None,
) -> Any:
    return get_merged_plugin_settings(window=window or sublime.active_window()).get(key, default)


def get_merged_plugin_settings(*, window: sublime.Window | None = None) -> MergedSettingsDict:
    return AioSettings.get_all(window or sublime.active_window())


def get_st_setting(key: str, default: Any | None = None) -> Any:
    # Preferences are not layered through `AioSettings`, which is what drops explicit nulls
    value = get_st_settings().get(key, default)
    return default if value is None else value


def get_st_settings() -> sublime.Settings:
    return sublime.load_settings("Preferences.sublime-settings")


SYNTAX_RULE_SOURCES: Final = ("core_syntax_rules", "project_syntax_rules", "user_syntax_rules", "default_syntax_rules")
"""The settings syntax rules come from, in the order they're tested (the first matching rule wins)."""


def pref_syntax_rules(*, window: sublime.Window | None = None) -> tuple[list[StSyntaxRule], list[DroppedRule]]:
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


def pref_trim_suffixes(*, window: sublime.Window | None = None) -> tuple[str, ...]:
    # default must be a tuple, not a list: this flows into build_reversed_trie(), which is
    # lru_cache-decorated and requires a hashable argument
    return get_merged_plugin_setting("trim_suffixes", (), window=window)


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


def extra_settings_producer(settings: MergedSettingsDict) -> dict[str, Any]:
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


class AioSettings(sublime_plugin.EventListener):
    """
    All-in-one settings for the plugin.

    This class provides merged settings of plugin settings and project settings.
    """

    plugin_name: str = ""
    """The plugin name. This should be set before using this plugin."""

    _on_settings_change_callbacks: ClassVar[dict[str, Callable[[sublime.Window], None]]] = {}
    _plugin_settings_object: ClassVar[sublime.Settings | None] = None
    _settings_producer: ClassVar[Callable[[MergedSettingsDict], dict[str, Any]] | None] = None
    _tracked_windows: ClassVar[set[int]] = set()

    # application-level
    _plugin_settings: ClassVar[SettingsDict] = {}

    # window-level
    _project_plugin_settings: ClassVar[dict[WindowId, SettingsDict]] = {}
    _merged_plugin_settings: ClassVar[dict[WindowId, MergedSettingsDict]] = {}

    # ----------- #
    # public APIs #
    # ----------- #

    @classmethod
    def set_up(cls) -> None:
        cls._plugin_settings_object = sublime.load_settings(f"{cls.plugin_name}.sublime-settings")
        cls._plugin_settings_object.add_on_change(cls.__name__, cls._on_settings_change)
        cls._on_settings_change()

    @classmethod
    def tear_down(cls) -> None:
        if cls._plugin_settings_object is not None:
            cls._plugin_settings_object.clear_on_change(cls.__name__)
            cls._plugin_settings_object = None
        cls._tracked_windows.clear()
        cls._plugin_settings.clear()
        cls._project_plugin_settings.clear()
        cls._merged_plugin_settings.clear()

    @classmethod
    def add_on_change(cls, key: str, callback: Callable) -> None:
        cls._on_settings_change_callbacks[key] = callback

    @classmethod
    def clear_on_change(cls, key: str) -> None:
        cls._on_settings_change_callbacks.pop(key, None)

    @classmethod
    def set_settings_producer(cls, producer: Callable[[MergedSettingsDict], dict[str, Any]] | None) -> None:
        cls._settings_producer = producer

    @classmethod
    def get_all(cls, window: sublime.Window) -> MergedSettingsDict:
        return cls._merged_plugin_settings.get(window.id()) or {}

    # ---------- #
    # listerners #
    # ---------- #

    def on_new(self, view: sublime.View) -> None:
        cls = self.__class__
        if not (window := view.window()) or cls._is_tracked_window(window):
            return
        # `on_settings_change` is used here to guarantee a newly created window is initialized
        # because `on_new` will be fired before `on_new_window` when creating a new window.
        cls._on_settings_change([window], run_callbacks=False)

    def on_new_window(self, window: sublime.Window) -> None:
        cls = self.__class__
        if cls._is_tracked_window(window):
            return
        cls._on_settings_change([window])

    def on_pre_close_window(self, window: sublime.Window) -> None:
        cls = self.__class__
        window_id = window.id()
        cls._merged_plugin_settings.pop(window_id, None)
        cls._project_plugin_settings.pop(window_id, None)
        cls._tracked_windows.discard(window_id)

    def on_load_project_async(self, window: sublime.Window) -> None:
        """
        Will be called after saving project settings.
        Somehow this has to be async in order to re-compile rules for a newly loaded project...
        """
        cls = self.__class__
        cls._on_settings_change([window])

    # ------------ #
    # private APIs #
    # ------------ #

    @classmethod
    def _is_tracked_window(cls, window: sublime.Window) -> bool:
        return window.id() in cls._tracked_windows

    @classmethod
    def _on_settings_change(cls, windows: list[sublime.Window] | None = None, run_callbacks: bool = True) -> None:
        if windows is None:
            # refresh all windows
            windows = sublime.windows()
            cls._update_plugin_settings()

        for window in windows:
            cls._update_project_plugin_settings(window)
            cls._update_merged_plugin_settings(window)
            cls._tracked_windows.add(window.id())

            if run_callbacks:
                for callback in cls._on_settings_change_callbacks.values():
                    callback(window)

    @classmethod
    def _update_plugin_settings(cls) -> None:
        assert cls._plugin_settings_object
        cls._plugin_settings = {"__comment": "plugin_settings"} | _drop_nulls(cls._plugin_settings_object.to_dict())

    @classmethod
    def _update_project_plugin_settings(cls, window: sublime.Window) -> None:
        window_id = window.id()
        project_settings = _as_dict((window.project_data() or {}).get("settings"))
        cls._project_plugin_settings[window_id] = {"__comment": "project_settings"} | _drop_nulls(
            _as_dict(project_settings.get(cls.plugin_name))
        )

    @classmethod
    def _update_merged_plugin_settings(cls, window: sublime.Window) -> None:
        window_id = window.id()

        merged = ChainMap(
            cls._project_plugin_settings.get(window_id) or {},
            cls._plugin_settings,
        )

        produced = {"__comment": "produced_settings"}
        if cls._settings_producer:
            produced.update(cls._settings_producer(merged))

        cls._merged_plugin_settings[window_id] = ChainMap(produced, *(merged.maps))
