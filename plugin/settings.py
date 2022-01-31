from __future__ import annotations

# __future__ must be the first import
from .types import ST_SyntaxRule
from collections import ChainMap
from itertools import chain
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Set, Tuple
import sublime
import sublime_plugin


def get_merged_plugin_setting(
    key: str,
    default: Optional[Any] = None,
    *,
    window: Optional[sublime.Window] = None,
) -> Any:
    return get_merged_plugin_settings(window=window or sublime.active_window()).get(key, default)


def get_merged_plugin_settings(*, window: Optional[sublime.Window] = None) -> MergedSettingsDict:
    return AioSettings.get_all(window or sublime.active_window())


def get_st_setting(key: str, default: Optional[Any] = None) -> Any:
    return get_st_settings().get(key, default)


def get_st_settings() -> sublime.Settings:
    return sublime.load_settings("Preferences.sublime-settings")


def pref_syntax_rules(*, window: Optional[sublime.Window] = None) -> List[ST_SyntaxRule]:
    return get_merged_plugin_setting("syntax_rules", [], window=window)


def pref_trim_suffixes(*, window: Optional[sublime.Window] = None) -> Tuple[str]:
    return get_merged_plugin_setting("trim_suffixes", [], window=window)


def extra_settings_producer(settings: MergedSettingsDict) -> Dict[str, Any]:
    ret: Dict[str, Any] = {}

    ret["syntax_rules"] = (
        settings.get("core_syntax_rules", [])
        + settings.get("project_syntax_rules", [])
        + settings.get("user_syntax_rules", [])
        + settings.get("default_syntax_rules", [])
    )

    # use tuple to freeze setting for better performance (cache)
    ret["trim_suffixes"] = tuple(
        # remove empty string, which causes an infinite loop
        filter(
            None,
            set(
                chain(
                    settings.get("project_trim_suffixes", []),
                    settings.get("user_trim_suffixes", []),
                    settings.get("default_trim_suffixes", []),
                )
            ),
        ),
    )

    return ret


SettingsDict = MutableMapping[str, Any]
MergedSettingsDict = Mapping[str, Any]
WindowId = int


class AioSettings(sublime_plugin.EventListener):
    plugin_name: str = ""

    _on_settings_change_callbacks: Dict[str, Callable[[sublime.Window], None]] = {}
    _plugin_settings_object: Optional[sublime.Settings] = None
    _settings_normalizer: Optional[Callable[[SettingsDict], None]] = None
    _settings_producer: Optional[Callable[[MergedSettingsDict], Dict[str, Any]]] = None
    _tracked_windows: Set[int] = set()

    # application-level
    _plugin_settings: SettingsDict = {}

    # window-level
    _project_plugin_settings: Dict[WindowId, SettingsDict] = {}
    _merged_plugin_settings: Dict[WindowId, MergedSettingsDict] = {}

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
        assert cls._plugin_settings_object
        cls._plugin_settings_object.clear_on_change(cls.__name__)

    @classmethod
    def add_on_change(cls, key: str, callback: Callable) -> None:
        cls._on_settings_change_callbacks[key] = callback

    @classmethod
    def clear_on_change(cls, key: str) -> None:
        cls._on_settings_change_callbacks.pop(key, None)

    @classmethod
    def set_settings_normalizer(cls, normalizer: Optional[Callable[[SettingsDict], None]]) -> None:
        cls._settings_normalizer = normalizer

    @classmethod
    def set_settings_producer(cls, producer: Optional[Callable[[MergedSettingsDict], Dict[str, Any]]]) -> None:
        cls._settings_producer = producer

    @classmethod
    def get(cls, window: sublime.Window, key: str, default: Optional[Any] = None) -> Any:
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
        cls._tracked_windows.remove(window_id)

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
    def _on_settings_change(cls, windows: Optional[List[sublime.Window]] = None, run_callbacks: bool = True) -> None:
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
        cls._plugin_settings = {"_comment": "plugin_settings"}
        cls._plugin_settings.update(cls._plugin_settings_object.to_dict())
        if cls._settings_normalizer:
            cls._settings_normalizer(cls._plugin_settings)

    @classmethod
    def _update_project_plugin_settings(cls, window: sublime.Window) -> None:
        window_id = window.id()
        cls._project_plugin_settings[window_id] = {"_comment": "project_settings"}
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

        produced = {"_comment": "produced_settings"}
        if cls._settings_producer:
            produced.update(cls._settings_producer(merged))

        cls._merged_plugin_settings[window_id] = ChainMap(produced, *(merged.maps))
