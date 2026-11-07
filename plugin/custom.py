import importlib
import importlib.machinery
import pkgutil
import sys
import traceback
from pathlib import Path
from typing import Any

import sublime

from .constants import PLUGIN_CUSTOM_DIR
from .constants import PLUGIN_CUSTOM_MODULE_PATHS
from .constants import PLUGIN_NAME
from .rules import AbstractConstraint
from .rules import AbstractMatch
from .utils import list_all_subclasses


def load_custom_implementations() -> None:
    _forget_custom_modules()
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
    warn_legacy_fold_overrides(AbstractConstraint, AbstractMatch)


def _forget_custom_modules() -> None:
    """
    Drop the custom package from `sys.modules` so the next import executes it afresh.

    On a plugin reload, `boot.py` re-imports `AutoSetSyntax.*` but not the custom package, so
    `import_module()` would hand back the cached module, whose classes subclass the *previous*
    `AbstractConstraint`/`AbstractMatch` -- invisible to the new ones' `__subclasses__()`, so every
    custom implementation would silently vanish. It also makes a reload pick up edited files.
    """
    root = PLUGIN_CUSTOM_DIR.name  # like "AutoSetSyntax-Custom"
    for name in [name for name in sys.modules if name == root or name.startswith(f"{root}.")]:
        del sys.modules[name]
    # the custom files may have been added since the directory listing was cached
    importlib.invalidate_caches()


_LEGACY_METHOD_NAMES = ("is_droppable", "droppable_value")
"""The methods `fold()` replaced. Overriding one no longer does anything."""


def warn_legacy_fold_overrides(*bases: type[Any]) -> None:
    """
    Warn about custom implementations still overriding the methods `fold()` replaced.

    A custom constraint/match that overrides `is_droppable()`/`droppable_value()` isn't broken
    -- it just silently stops being optimized away, since nothing calls those names any more.
    A silent loss of optimization is a miserable thing to debug, so say so at load time.
    """
    for base in bases:
        for cls in list_all_subclasses(base, skip_self=True):
            if legacy := [name for name in _LEGACY_METHOD_NAMES if name in vars(cls)]:
                print(
                    f"[{PLUGIN_NAME}][WARNING] {cls.__module__}.{cls.__qualname__} overrides"
                    f" {'/'.join(legacy)}, which is no longer used."
                    " Rename it to fold(), returning Fold(True/False, reason) for a constant result"
                    " or UNFOLDED when the result still depends on the view."
                )
