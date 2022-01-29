from .commands.auto_set_syntax import run_auto_set_syntax_on_view
from .constant import PLUGIN_CUSTOM_MODULE_PATHS
from .constant import PLUGIN_NAME
from .guesslang.server import GuesslangServer
from .helper import remove_prefix
from .listener import compile_rules
from .listener import set_up_window
from .listener import tear_down_window
from .lru_cache import clear_all_cached_functions
from .rules import AbstractConstraint
from .rules import AbstractMatch
from .rules import MatchableRule
from .settings import AioSettings
from .settings import extra_settings_producer
from .settings import get_merged_plugin_setting
from .shared import G
from .types import ListenerEvent
from pathlib import Path
import importlib
import importlib.machinery
import pkgutil
import sublime

__all__ = (
    "AbstractConstraint",
    "AbstractMatch",
    "MatchableRule",
    "set_up",
    "tear_down",
)


def set_up() -> None:
    _load_custom_implementations()

    AioSettings.plugin_name = PLUGIN_NAME
    AioSettings.set_settings_producer(extra_settings_producer)
    AioSettings.set_up()
    AioSettings.add_on_change(PLUGIN_NAME, _settings_changed_callback)

    for window in sublime.windows():
        set_up_window(window)

    _run_on_init_views()
    sublime.run_command("auto_set_syntax_restart_guesslang")


def tear_down() -> None:
    AioSettings.clear_on_change(PLUGIN_NAME)
    AioSettings.tear_down()

    for window in sublime.windows():
        tear_down_window(window)

    GuesslangServer.stop()


def _settings_changed_callback(window: sublime.Window) -> None:
    clear_all_cached_functions()
    compile_rules(window, is_update=True)


def _load_custom_implementations():
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


def _run_on_init_views() -> None:
    if get_merged_plugin_setting("run_on_startup_views"):
        for view in G.views_on_init:
            run_auto_set_syntax_on_view(view, ListenerEvent.INIT)
