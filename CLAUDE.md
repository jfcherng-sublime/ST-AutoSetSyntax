# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoSetSyntax is a Sublime Text 4 plugin that automatically sets the syntax (language) for a view using multiple detection strategies: user-defined rules, first-line matching (shebang/modeline), filename trimming, and optional deep-learning detection via Google's Magika.

The plugin runs inside Sublime Text's embedded Python 3.13 interpreter. You may use any features up to Python 3.13.

## Commands

Dependencies are managed with `uv`. Use the Makefile targets:

```bash
make install-dev    # install dev dependencies
make ci-check       # run mypy + ruff lint + ruff format checks (read-only)
make ci-fix         # auto-fix ruff lint and format issues
make ci-fix-unsafe  # same but with ruff --unsafe-fixes
make test           # unittest
```

Individual tools:

```bash
uv run --dev mypy -p plugin          # type-check the plugin package
uv run --dev ruff check --diff .     # lint
uv run --dev ruff format --diff .    # format check
```

There is no automated test runner (the `tests/` directory only contains fixture files). Testing requires loading the plugin in Sublime Text.

## Code Style

- **Line length**: 120 characters
- **Ruff**: runs in `preview = true` mode; selected rules: `E, F, FURB, I, PERF, SIM, UP, W`
- **Indentation**: 4 spaces for `.py` and `.json`; 2 spaces for `.md`, `.toml`, Sublime configs; tabs for `Makefile`
- `_vendor/`, `typings/`, `stubs/`, `tests/files/`, and `branch-*` directories are excluded from ruff and mypy

## Git Conventions

- Feature branches use the `branch-` prefix (e.g., `branch-my-feature`)
- Main development branch: `st4`

## Architecture

### Entry Points

- **`boot.py`** — ST plugin bootstrap: clears cached modules on reload, then imports everything from `plugin/`.
- **`plugin/__init__.py`** — Defines `plugin_loaded()` / `plugin_unloaded()` (ST lifecycle hooks) and the public API surface (`AbstractConstraint`, `AbstractMatch`, `MatchableRule`, `ViewSnapshot`).

### Rules System (`plugin/rules/`)

Class naming convention: `FooBarMatch` → name `"foo_bar"`, `FooBarConstraint` → name `"foo_bar"`. Names are auto-derived via `camel_to_snake` and matched against settings strings.

- **`AbstractMatch`** — base class for `any`, `all`, `some`, `ratio` match types; `test()` receives a `ViewSnapshot` and child `MatchableRule`s
- **`AbstractConstraint`** — base class for leaf conditions (`is_extension`, `contains_regex`, `is_syntax`, etc.); `test()` returns bool
- **`SyntaxRule`** — top-level rule with `selector`, `on_events`, `syntaxes`, and a root `MatchRule`
- **`SyntaxRuleCollection`** — ordered list of `SyntaxRule`; returns the first matching rule

### Extensibility

Users can add custom `Match`/`Constraint` implementations by placing Python files in `AutoSetSyntax-Custom/matches/` or `AutoSetSyntax-Custom/constraints/` under ST's Packages directory. These are auto-discovered at load time via `_load_custom_implementations()`.

### Optional Magika Integration

Magika (Google's deep-learning file type detector) is an optional dependency downloaded separately. Only invoked for plain-text files without extensions (unless triggered via command).

### Vendored Dependencies

`plugin/_vendor/` contains vendored Python packages (managed via `vendorize.toml`). Ignored by mypy and ruff.
