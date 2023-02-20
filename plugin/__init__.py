import importlib
import importlib.machinery
import pkgutil
from pathlib import Path

import sublime

from .cache import clear_all_cached_functions
from .commands import (
    AutoSetSyntaxCommand,
    AutoSetSyntaxCreateNewConstraintCommand,
    AutoSetSyntaxCreateNewMatchCommand,
    AutoSetSyntaxDebugInformationCommand,
    AutoSetSyntaxDownloadGuesslangServerCommand,
    AutoSetSyntaxRestartGuesslangCommand,
    run_auto_set_syntax_on_view,
)
from .constants import PLUGIN_CUSTOM_MODULE_PATHS, PLUGIN_NAME
from .listener import (
    AutoSetSyntaxEventListener,
    AutoSetSyntaxTextChangeListener,
    compile_rules,
    set_up_window,
    tear_down_window,
)
from .logger import AutoSetSyntaxAppendLogCommand, AutoSetSyntaxClearLogPanelCommand, AutoSetSyntaxToggleLogPanelCommand
from .rules import AbstractConstraint, AbstractMatch, MatchableRule
from .settings import AioSettings, extra_settings_producer, get_merged_plugin_setting
from .shared import G
from .types import ListenerEvent
from .utils import remove_prefix

__all__ = (
    # ST: core
    "plugin_loaded",
    "plugin_unloaded",
    # ST: commands (logging)
    "AutoSetSyntaxAppendLogCommand",
    "AutoSetSyntaxClearLogPanelCommand",
    "AutoSetSyntaxToggleLogPanelCommand",
    # ST: commands
    "AutoSetSyntaxCommand",
    "AutoSetSyntaxCreateNewConstraintCommand",
    "AutoSetSyntaxCreateNewMatchCommand",
    "AutoSetSyntaxDebugInformationCommand",
    "AutoSetSyntaxDownloadGuesslangServerCommand",
    "AutoSetSyntaxRestartGuesslangCommand",
    # ST: listeners
    "AioSettings",
    "AutoSetSyntaxEventListener",
    "AutoSetSyntaxTextChangeListener",
    # public interfaces
    "AbstractConstraint",
    "AbstractMatch",
    "MatchableRule",
)


def plugin_loaded() -> None:
    # somehow "AutoSetSyntaxAppendLogCommand" won't be ready if we don't wait a bit
    sublime.set_timeout(_plugin_loaded)


def _plugin_loaded() -> None:
    _load_custom_implementations()

    AioSettings.plugin_name = PLUGIN_NAME
    AioSettings.set_settings_producer(extra_settings_producer)
    AioSettings.set_up()
    AioSettings.add_on_change(PLUGIN_NAME, _settings_changed_callback)

    for window in sublime.windows():
        set_up_window(window)

    sublime.set_timeout_async(_run_on_startup_views)
    sublime.run_command("auto_set_syntax_restart_guesslang")


def plugin_unloaded() -> None:
    AioSettings.clear_on_change(PLUGIN_NAME)
    AioSettings.tear_down()

    for window in sublime.windows():
        tear_down_window(window)

    if G.guesslang_server:
        G.guesslang_server.stop()


def _settings_changed_callback(window: sublime.Window) -> None:
    clear_all_cached_functions()
    compile_rules(window, is_update=True)


def _load_custom_implementations() -> None:
    for finder, name, _ in pkgutil.iter_modules(map(str, PLUGIN_CUSTOM_MODULE_PATHS.values())):
        assert isinstance(finder, importlib.machinery.FileFinder)
        # something like "AutoSetSyntax-Custom/matches"
        module_relative_path = Path(remove_prefix(finder.path, sublime.packages_path())).as_posix().strip("/")
        # something like "AutoSetSyntax-Custom.matches"
        module_base = module_relative_path.replace("/", ".")
        module_name = f"{module_base}.{name}"
        try:
            importlib.import_module(module_name)
            print(f"[{PLUGIN_NAME}] Load custom Implementation: {module_name}")
        except ImportError as e:
            print(f"[{PLUGIN_NAME}] _load_custom_implementations: {e}")


def _run_on_startup_views() -> None:
    if get_merged_plugin_setting("run_on_startup_views"):
        for view in G.startup_views:
            run_auto_set_syntax_on_view(view, ListenerEvent.INIT)
