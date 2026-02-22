# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoSetSyntax is a Sublime Text 4 plugin that automatically sets the syntax (language) for a view using multiple detection strategies: user-defined rules, first-line matching (shebang/modeline), filename trimming, and optional deep-learning detection via Google's Magika.

The plugin runs inside Sublime Text's embedded Python 3.8 interpreter at runtime, but the development toolchain targets Python 3.13.

## Commands

Dependencies are managed with `uv`. Use the Makefile targets:

```bash
make install-dev    # install dev dependencies
make ci-check       # run mypy + ruff lint + ruff format checks (read-only)
make ci-fix         # auto-fix ruff lint and format issues
make ci-fix-unsafe  # same but with ruff --unsafe-fixes
```

Individual tools:

```bash
uv run --dev mypy -p plugin          # type-check the plugin package
uv run --dev ruff check --diff .     # lint
uv run --dev ruff format --diff .    # format check
```

There is no automated test runner (the `tests/` directory only contains fixture files). Testing requires loading the plugin in Sublime Text.

## Architecture

### Entry Points

- **`boot.py`** — ST plugin bootstrap: clears cached modules on reload, then imports everything from `plugin/`.
- **`plugin/__init__.py`** — Defines `plugin_loaded()` / `plugin_unloaded()` (ST lifecycle hooks) and the public API surface (`AbstractConstraint`, `AbstractMatch`, `MatchableRule`, `ViewSnapshot`).

### Core Data Flow

1. **Settings merge** (`plugin/settings.py`) — Settings are per-window, merging `core_syntax_rules` + `project_syntax_rules` + `user_syntax_rules` + `default_syntax_rules` into a unified `syntax_rules` list. The `AioSettings` class handles change callbacks.

2. **Rule compilation** (`plugin/listener.py:compile_rules`) — On plugin load or settings change, `StSyntaxRule` pydantic models are built from settings JSON, then compiled into a `SyntaxRuleCollection` object (a tree of `SyntaxRule` → `MatchRule` → `ConstraintRule` objects). Rules are then optimized (invalid/unreachable ones dropped).

3. **Global state** (`plugin/shared.py:G`) — Class `G` holds per-window `SyntaxRuleCollections` and `DroppedRulesCollection` as class variables.

4. **Event listeners** (`plugin/listener.py`) — `AutoSetSyntaxEventListener` and `AutoSetSyntaxTextChangeListener` respond to ST events (load, save, new, modify, paste, revert, etc.) and call `run_auto_set_syntax_on_view()`.

5. **Syntax assignment pipeline** (`plugin/commands/auto_set_syntax.py:run_auto_set_syntax_on_view`) — Tries strategies in order:
   - ST syntax test files (filename starts with `syntax_test_`)
   - Plugin rules (`SyntaxRuleCollection.test(view_snapshot, event)`)
   - First-line matching (shebang `#!`, Emacs/Vim modelines, ST's built-in first-line detection)
   - Trimmed filename (strips suffixes like `.bak`, `.tmp`)
   - Magika deep-learning detection (if enabled and available)
   - Heuristics (e.g., JSON content detection)

6. **ViewSnapshot** (`plugin/snapshot.py`) — Frozen dataclass capturing view state (content, first line, file path, syntax, encoding, etc.) at rule-test time. Uses `cached_property` for expensive derived values. Content is trimmed to `trim_file_size` bytes.

### Rules System (`plugin/rules/`)

- **`AbstractMatch`** (base class for `any`, `all`, `some`, `ratio` match types) — Groups sub-rules; `test()` receives a `ViewSnapshot` and a tuple of child `MatchableRule`s.
- **`AbstractConstraint`** (base class for all leaf conditions like `is_extension`, `contains_regex`, `is_syntax`, etc.) — `test()` receives a `ViewSnapshot` and returns bool.
- **`SyntaxRule`** — Top-level rule with `selector` (scope filter), `on_events` (event filter), `syntaxes` (target syntaxes list), and a root `MatchRule`.
- **`SyntaxRuleCollection`** — Ordered list of `SyntaxRule`; returns the first matching rule.

Class naming convention: `FooBarMatch` → name `"foo_bar"`, `FooBarConstraint` → name `"foo_bar"`. Names are auto-derived via `camel_to_snake` and matched against settings strings.

### Extensibility

Users can add custom `Match`/`Constraint` implementations by placing Python files in `AutoSetSyntax-Custom/matches/` or `AutoSetSyntax-Custom/constraints/` under ST's Packages directory. These are auto-discovered at load time via `_load_custom_implementations()`.

### Optional Magika Integration

Magika (Google's deep-learning file type detector) is an optional dependency downloaded separately. `plugin/magika.py` wraps it with a cached accessor. It is only invoked for plain-text files without extensions (unless triggered via command).

### Vendored Dependencies

`plugin/_vendor/` contains vendored Python packages (managed via `vendorize.toml`). Currently just a trie implementation.

## Key Files

| File                                 | Purpose                                                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------------------- |
| `plugin/types.py`                    | Pydantic models (`StSyntaxRule`, `StMatchRule`, `StConstraintRule`) and `ListenerEvent` enum |
| `plugin/snapshot.py`                 | `ViewSnapshot` — immutable view state for rule testing                                       |
| `plugin/shared.py`                   | Global state holder `G`                                                                      |
| `plugin/listener.py`                 | ST event listeners + `compile_rules()`                                                       |
| `plugin/commands/auto_set_syntax.py` | Main assignment pipeline                                                                     |
| `plugin/rules/constraint.py`         | `AbstractConstraint` base + `ConstraintRule`                                                 |
| `plugin/rules/match.py`              | `AbstractMatch` base + `MatchRule`                                                           |
| `plugin/rules/syntax.py`             | `SyntaxRule` + `SyntaxRuleCollection`                                                        |
| `plugin/rules/constraints/`          | All built-in constraint implementations                                                      |
| `plugin/rules/matches/`              | All built-in match implementations (`any`, `all`, `some`, `ratio`)                           |
| `typings/`                           | Type stubs for `sublime` and `sublime_plugin` APIs                                           |
