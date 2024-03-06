import importlib
import importlib.machinery
import pkgutil
import sys
from pathlib import Path

import sublime

from .cache import clear_all_cached_functions
from .commands import (
    AutoSetSyntaxCommand,
    AutoSetSyntaxCreateNewConstraintCommand,
    AutoSetSyntaxCreateNewMatchCommand,
    AutoSetSyntaxDebugInformationCommand,
    AutoSetSyntaxDownloadDependenciesCommand,
    run_auto_set_syntax_on_view,
)
from .constants import PLUGIN_CUSTOM_MODULE_PATHS, PLUGIN_NAME, PLUGIN_PY_LIBS_DIR
from .listener import (
    AutoSetSyntaxEventListener,
    AutoSetSyntaxTextChangeListener,
    compile_rules,
    set_up_window,
    tear_down_window,
)
from .logger import (
    AutoSetSyntaxAppendLogCommand,
    AutoSetSyntaxClearLogPanelCommand,
    AutoSetSyntaxToggleLogPanelCommand,
    AutoSetSyntaxUpdateLogCommand,
)
from .rules import AbstractConstraint, AbstractMatch, MatchableRule
from .settings import AioSettings, extra_settings_producer, get_merged_plugin_setting
from .shared import G
from .snapshot import ViewSnapshot
from .types import ListenerEvent

__all__ = (
    # ST: core
    "plugin_loaded",
    "plugin_unloaded",
    # ST: commands (logging)
    "AutoSetSyntaxAppendLogCommand",
    "AutoSetSyntaxClearLogPanelCommand",
    "AutoSetSyntaxToggleLogPanelCommand",
    "AutoSetSyntaxUpdateLogCommand",
    # ST: commands
    "AutoSetSyntaxCommand",
    "AutoSetSyntaxCreateNewConstraintCommand",
    "AutoSetSyntaxCreateNewMatchCommand",
    "AutoSetSyntaxDebugInformationCommand",
    "AutoSetSyntaxDownloadDependenciesCommand",
    # ST: listeners
    "AioSettings",
    "AutoSetSyntaxEventListener",
    "AutoSetSyntaxTextChangeListener",
    # public interfaces
    "AbstractConstraint",
    "AbstractMatch",
    "MatchableRule",
    "ViewSnapshot",
)


def plugin_loaded() -> None:
    # somehow "AutoSetSyntaxAppendLogCommand" won't be ready if we don't wait a bit
    sublime.set_timeout(_plugin_loaded)


def _plugin_loaded() -> None:
    _add_python_lib_path()
    _load_custom_implementations()

    AioSettings.plugin_name = PLUGIN_NAME
    AioSettings.set_settings_producer(extra_settings_producer)
    AioSettings.set_up()
    AioSettings.add_on_change(PLUGIN_NAME, _settings_changed_callback)

    for window in sublime.windows():
        set_up_window(window)

    if get_merged_plugin_setting("run_on_startup_views"):
        sublime.set_timeout_async(_run_on_startup_views)


def plugin_unloaded() -> None:
    AioSettings.clear_on_change(PLUGIN_NAME)
    AioSettings.tear_down()

    for window in sublime.windows():
        tear_down_window(window)


def _settings_changed_callback(window: sublime.Window) -> None:
    clear_all_cached_functions()
    compile_rules(window, is_update=True)


def _add_python_lib_path() -> None:
    if (path := str(PLUGIN_PY_LIBS_DIR)) not in sys.path:
        sys.path.insert(0, path)


def _load_custom_implementations() -> None:
    for finder, name, _ in pkgutil.iter_modules(map(str, PLUGIN_CUSTOM_MODULE_PATHS.values())):
        assert isinstance(finder, importlib.machinery.FileFinder)
        # something like "AutoSetSyntax-Custom/matches"
        module_relpath = Path(finder.path).relative_to(sublime.packages_path()).as_posix()
        # something like "AutoSetSyntax-Custom.matches"
        module_base = module_relpath.replace("/", ".")
        module_name = f"{module_base}.{name}"
        try:
            importlib.import_module(module_name)
            print(f"[{PLUGIN_NAME}][INFO] Load custom implementation: {module_name}")
        except ImportError as e:
            print(f"[{PLUGIN_NAME}][ERROR] Failed loading custom implementation: {e}")


def _run_on_startup_views() -> None:
    for view in G.startup_views:
        run_auto_set_syntax_on_view(view, ListenerEvent.INIT)
