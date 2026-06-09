"""
Inject minimal sublime / sublime_plugin stubs into sys.modules before any
plugin code is imported, so that unit tests can run outside Sublime Text.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent


# ── Sublime Text stubs ────────────────────────────────────────────────────────


def _make_sublime_stub() -> ModuleType:
    mod = ModuleType("sublime")

    # Platform / environment
    mod.arch = lambda: "x64"
    mod.channel = lambda: "dev"
    mod.platform = lambda: "linux"
    mod.version = lambda: "4000"
    mod.cache_path = lambda: "/tmp/st_cache"
    mod.packages_path = lambda: "/tmp/st_packages"
    mod.installed_packages_path = lambda: "/tmp/st_installed"
    mod.executable_path = lambda: "/tmp/sublime_text"

    # Common API helpers
    mod.active_window = lambda: MagicMock()
    mod.windows = lambda: []
    mod.list_syntaxes = lambda: []
    mod.find_syntax_by_scope = lambda scope: []
    mod.find_syntax_by_name = lambda name: []
    mod.expand_variables = lambda value, variables=None: value
    mod.set_timeout_async = lambda func, delay=0: None
    mod.score_selector = lambda scope, selector: 0
    mod.load_settings = lambda name: MagicMock()

    class Region:
        def __init__(self, a: int, b: int | None = None) -> None:
            self.a = a
            self.b = b if b is not None else a

        def to_tuple(self) -> tuple[int, int]:
            return (self.a, self.b)

    class View:
        def is_valid(self) -> bool:
            return True

        def window(self) -> MagicMock:
            return MagicMock()

        def id(self) -> int:
            return 0

    class Syntax:
        def __init__(self, path: str = "", name: str = "", hidden: bool = False, scope: str = "") -> None:
            self.path = path
            self.name = name
            self.hidden = hidden
            self.scope = scope

    class Window:
        def is_valid(self) -> bool:
            return True

        def id(self) -> int:
            return 0

    class Buffer:
        pass

    class Sheet:
        def is_transient(self) -> bool:
            return False

    class Edit:
        pass

    class Settings:
        def get(self, key: str, default=None):
            return default

        def set(self, key: str, value) -> None:
            pass

        def add_on_change(self, key: str, callback) -> None:
            pass

        def clear_on_change(self, key: str) -> None:
            pass

    mod.Region = Region
    mod.View = View
    mod.Syntax = Syntax
    mod.Window = Window
    mod.Buffer = Buffer
    mod.Sheet = Sheet
    mod.Edit = Edit
    mod.Settings = Settings
    return mod


def _make_sublime_plugin_stub() -> ModuleType:
    mod = ModuleType("sublime_plugin")

    class _BaseCommand:
        pass

    class TextCommand(_BaseCommand):
        def __init__(self, view) -> None:
            self.view = view

    class WindowCommand(_BaseCommand):
        def __init__(self, window) -> None:
            self.window = window

    class ApplicationCommand(_BaseCommand):
        pass

    class EventListener:
        pass

    class ViewEventListener:
        pass

    class TextInputHandler:
        pass

    class ListInputHandler:
        pass

    mod.TextCommand = TextCommand
    mod.WindowCommand = WindowCommand
    mod.ApplicationCommand = ApplicationCommand
    mod.EventListener = EventListener
    mod.ViewEventListener = ViewEventListener
    mod.TextInputHandler = TextInputHandler
    mod.ListInputHandler = ListInputHandler
    return mod


def _make_plugin_package_stub() -> ModuleType:
    """
    Create a stub for the 'plugin' package that exposes its submodule search
    path but skips running plugin/__init__.py (which imports the full ST plugin
    machinery and fails outside Sublime Text).
    """
    spec = importlib.machinery.ModuleSpec(
        "plugin",
        loader=None,
        origin=None,
        is_package=True,
    )
    spec.submodule_search_locations = [str(_PROJECT_ROOT / "plugin")]
    pkg = importlib.util.module_from_spec(spec)
    pkg.__package__ = "plugin"
    return pkg


# Inject before any plugin code is loaded
if "sublime" not in sys.modules:
    sys.modules["sublime"] = _make_sublime_stub()
if "sublime_plugin" not in sys.modules:
    sys.modules["sublime_plugin"] = _make_sublime_plugin_stub()
if "plugin" not in sys.modules:
    sys.modules["plugin"] = _make_plugin_package_stub()


# ── Shared fixtures ───────────────────────────────────────────────────────────

TESTS_DIR = Path(__file__).parent
FIXTURE_DIR = TESTS_DIR / "files"


@pytest.fixture(autouse=True)
def clear_plugin_caches():
    """Clear all clearable_lru_cache entries between tests."""
    yield
    from plugin.cache import clear_all_cached_functions

    clear_all_cached_functions()


@pytest.fixture()
def make_snapshot():
    """
    Factory fixture that constructs a ViewSnapshot with controllable fields.

    Usage::

        def test_foo(make_snapshot):
            snap = make_snapshot(content="hello", first_line="hello")
            assert MyConstraint("hello").test(snap)
    """
    from plugin.snapshot import ViewSnapshot

    MockView = sys.modules["sublime"].View

    def _factory(
        content: str = "",
        first_line: str = "",
        encoding: str = "UTF-8",
        line_count: int = 1,
        path: str | None = None,
        char_count: int | None = None,
        # Override the cached file_size property directly (use -1 for "not on disk")
        file_size: int | None = None,
    ) -> ViewSnapshot:
        snap = ViewSnapshot(
            view=MockView(),
            char_count=char_count if char_count is not None else len(content),
            encoding=encoding,
            line_count=line_count,
            path_obj=Path(path) if path else None,
            syntax=None,
        )
        # Pre-populate lazy cached properties so tests don't need a real view
        snap.__dict__["content"] = content
        snap.__dict__["first_line"] = first_line or (content.split("\n")[0] if content else "")
        # frozen dataclass: cached_property stores in __dict__ bypassing __setattr__
        if file_size is not None:
            snap.__dict__["file_size"] = file_size
        return snap

    return _factory
