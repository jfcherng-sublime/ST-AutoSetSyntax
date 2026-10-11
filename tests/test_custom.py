"""Tests for loading custom implementations across plugin reloads."""

import sys

import sublime

import plugin.custom as custom_mod

_ROOT = "zz-Custom"
"""A custom-package name no other test imports, so its `sys.modules` entries are this test's own."""


def _forget(root: str) -> None:
    for name in [name for name in sys.modules if name == root or name.startswith(f"{root}.")]:
        del sys.modules[name]


class TestReloadReExecutesCustomModules:
    """
    On a plugin reload, `boot.py` re-imports `AutoSetSyntax.*` but leaves the custom package in
    `sys.modules`. A cached custom module's classes subclass the *previous* `AbstractConstraint`,
    so they'd silently stop being implementations -- each load must execute the module afresh.
    """

    def test_second_load_runs_the_current_source(self, monkeypatch, tmp_path):
        custom_dir = tmp_path / _ROOT
        matches_dir = custom_dir / "matches"
        matches_dir.mkdir(parents=True)
        module_file = matches_dir / "mine.py"

        monkeypatch.setattr(sys, "dont_write_bytecode", True)  # a same-size rewrite could reuse a stale .pyc
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.setattr(sublime, "packages_path", lambda: str(tmp_path))
        monkeypatch.setattr(custom_mod, "PLUGIN_CUSTOM_DIR", custom_dir)
        monkeypatch.setattr(custom_mod, "PLUGIN_CUSTOM_MODULE_PATHS", {"match": matches_dir})
        try:
            module_file.write_text("GENERATION = 1\n", encoding="utf-8")
            custom_mod.load_custom_implementations()
            assert sys.modules[f"{_ROOT}.matches.mine"].GENERATION == 1

            module_file.write_text("GENERATION = 2\n", encoding="utf-8")
            custom_mod.load_custom_implementations()
            assert sys.modules[f"{_ROOT}.matches.mine"].GENERATION == 2
        finally:
            _forget(_ROOT)
