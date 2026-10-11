import importlib
import importlib.machinery
import pkgutil
import traceback
from pathlib import Path

import sublime

from .constants import PLUGIN_CUSTOM_MODULE_PATHS
from .constants import PLUGIN_NAME


def load_custom_implementations() -> None:
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
        except Exception:
            # user code can fail with anything (SyntaxError, NameError, ...), and that must not stop
            # the plugin from starting or the other custom modules from loading
            print(
                f"[{PLUGIN_NAME}][ERROR] Failed loading custom implementation: {module_name}\n{traceback.format_exc()}"
            )
