from collections import ChainMap
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import MutableMapping
from itertools import chain
from typing import Any
from typing import ClassVar

import sublime
import sublime_plugin
from more_itertools import unique_everseen
from pydantic import TypeAdapter

from .types import StSyntaxRule
from .utils import drop_falsy

type SettingsDict = MutableMapping[str, Any]
type MergedSettingsDict = Mapping[str, Any]
type WindowId = int


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
    return get_st_settings().get(key, default)


def get_st_settings() -> sublime.Settings:
    return sublime.load_settings("Preferences.sublime-settings")


def pref_syntax_rules(*, window: sublime.Window | None = None) -> list[StSyntaxRule]:
    return TypeAdapter(list[StSyntaxRule]).validate_python(get_merged_plugin_setting("syntax_rules", [], window=window))


def pref_trim_suffixes(*, window: sublime.Window | None = None) -> tuple[str, ...]:
    return get_merged_plugin_setting("trim_suffixes", [], window=window)


def extra_settings_producer(settings: MergedSettingsDict) -> dict[str, Any]:
    ret: dict[str, Any] = {}

    ret["syntax_rules"] = (
        settings.get("core_syntax_rules", [])
        + settings.get("project_syntax_rules", [])
        + settings.get("user_syntax_rules", [])
        + settings.get("default_syntax_rules", [])
    )

    # use tuple to freeze setting for better performance (cache-able)
    ret["trim_suffixes"] = tuple(
        drop_falsy(
            unique_everseen(
                chain(
                    settings.get("project_trim_suffixes", []),
                    settings.get("user_trim_suffixes", []),
                    settings.get("default_trim_suffixes", []),
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
    _settings_normalizer: ClassVar[Callable[[SettingsDict], None] | None] = None
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

    @classmethod
    def add_on_change(cls, key: str, callback: Callable) -> None:
        cls._on_settings_change_callbacks[key] = callback

    @classmethod
    def clear_on_change(cls, key: str) -> None:
        cls._on_settings_change_callbacks.pop(key, None)

    @classmethod
    def set_settings_normalizer(cls, normalizer: Callable[[SettingsDict], None] | None) -> None:
        cls._settings_normalizer = normalizer

    @classmethod
    def set_settings_producer(cls, producer: Callable[[MergedSettingsDict], dict[str, Any]] | None) -> None:
        cls._settings_producer = producer

    @classmethod
    def get(cls, window: sublime.Window, key: str, default: Any | None = None) -> Any:
        return cls.get_all(window).get(key, default)

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
        cls._plugin_settings = {"__comment": "plugin_settings"}
        cls._plugin_settings.update(cls._plugin_settings_object.to_dict())
        if cls._settings_normalizer:
            cls._settings_normalizer(cls._plugin_settings)

    @classmethod
    def _update_project_plugin_settings(cls, window: sublime.Window) -> None:
        window_id = window.id()
        cls._project_plugin_settings[window_id] = {"__comment": "project_settings"}
        cls._project_plugin_settings[window_id].update(
            (window.project_data() or {}).get("settings", {}).get(cls.plugin_name, {})
        )
        if cls._settings_normalizer:
            cls._settings_normalizer(cls._project_plugin_settings[window_id])

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
