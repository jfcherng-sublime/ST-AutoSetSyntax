import sys

import sublime

from .cache import clear_all_cached_functions
from .commands import AutoSetSyntaxCommand
from .commands import AutoSetSyntaxCreateNewConstraintCommand
from .commands import AutoSetSyntaxCreateNewMatchCommand
from .commands import AutoSetSyntaxDebugInformationCommand
from .commands import AutoSetSyntaxDownloadDependenciesCommand
from .commands import AutoSetSyntaxSyntaxRulesSummaryCommand
from .commands import remove_stale_dependency_dirs
from .commands import run_auto_set_syntax_on_view
from .constants import PLUGIN_NAME
from .constants import PLUGIN_PY_LIBS_DIR
from .custom import load_custom_implementations
from .listener import AutoSetSyntaxEventListener
from .listener import AutoSetSyntaxTextChangeListener
from .listener import compile_rules
from .listener import set_up_window
from .listener import tear_down_window
from .logger import AutoSetSyntaxAppendLogCommand
from .logger import AutoSetSyntaxClearLogPanelCommand
from .logger import AutoSetSyntaxToggleLogPanelCommand
from .logger import AutoSetSyntaxUpdateLogCommand
from .rules import AbstractConstraint
from .rules import AbstractMatch
from .rules import MatchableRule
from .rules._optimize import warn_legacy_fold_overrides
from .settings import AioSettings
from .settings import extra_settings_producer
from .settings import get_merged_plugin_setting
from .shared import G
from .snapshot import ViewSnapshot
from .types import UNFOLDED
from .types import Fold
from .types import ListenerEvent

__all__ = (
    # public interfaces
    "UNFOLDED",
    "AbstractConstraint",
    "AbstractMatch",
    # ST: listeners
    "AioSettings",
    # ST: commands (logging)
    "AutoSetSyntaxAppendLogCommand",
    "AutoSetSyntaxClearLogPanelCommand",
    # ST: commands
    "AutoSetSyntaxCommand",
    "AutoSetSyntaxCreateNewConstraintCommand",
    "AutoSetSyntaxCreateNewMatchCommand",
    "AutoSetSyntaxDebugInformationCommand",
    "AutoSetSyntaxDownloadDependenciesCommand",
    "AutoSetSyntaxEventListener",
    "AutoSetSyntaxSyntaxRulesSummaryCommand",
    "AutoSetSyntaxTextChangeListener",
    "AutoSetSyntaxToggleLogPanelCommand",
    "AutoSetSyntaxUpdateLogCommand",
    "Fold",
    "MatchableRule",
    "ViewSnapshot",
    # ST: core
    "plugin_loaded",
    "plugin_unloaded",
)


def plugin_loaded() -> None:
    """Executed when this plugin is loaded."""
    # somehow "AutoSetSyntaxAppendLogCommand" won't be ready if we don't wait a bit
    sublime.set_timeout(_plugin_loaded)


def _plugin_loaded() -> None:
    # old installs a dependency download left behind; they're never on `sys.path`, so safe anytime
    sublime.set_timeout_async(remove_stale_dependency_dirs)
    _add_python_lib_path()
    load_custom_implementations()
    warn_legacy_fold_overrides(AbstractConstraint, AbstractMatch)

    AioSettings.plugin_name = PLUGIN_NAME
    AioSettings.set_settings_producer(extra_settings_producer)
    AioSettings.set_up()
    AioSettings.add_on_change(PLUGIN_NAME, _settings_changed_callback)

    for window in sublime.windows():
        set_up_window(window)

    if get_merged_plugin_setting("run_on_startup_views"):
        sublime.set_timeout_async(_run_on_startup_views)


def plugin_unloaded() -> None:
    """Executed when this plugin is unloaded."""
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


def _run_on_startup_views() -> None:
    for view in G.startup_views:
        run_auto_set_syntax_on_view(view, ListenerEvent.INIT)
    G.startup_views.clear()
