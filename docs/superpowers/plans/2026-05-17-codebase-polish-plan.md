# Codebase Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incrementally improve AutoSetSyntax codebase — fix dead code, add dataclass slots/immutability, extract duplicated optimize pattern, clean up caching, refactor global state holder, and apply minor Python modernizations.

**Architecture:** Six mostly-independent tasks ordered by risk. Dead code fix and cache cleanup first (safe), then global state refactor (touches shared.py imported by everything), then structural changes (extract optimize helper + add dataclass slots).

**Tech Stack:** Python 3.14, Sublime Text 4 plugin API, ruff (E/F/FURB/I/PERF/SIM/UP/W), mypy.

---

## File Structure

### New files
- `plugin/rules/_optimize.py` — shared helper for the duplicated optimize-filter-optimize loop

### Modified files
- `plugin/rules/constraint.py` — dead code fix, `slots=True, frozen=True`
- `plugin/listener.py` — `_configured_debounce` lru_cache
- `plugin/shared.py` — `G` → module-level instance
- `plugin/cache.py` — remove private `_lru_cache_wrapper` import
- `plugin/types.py` — tighten `WindowKeyedDict.__contains__` type
- `plugin/rules/syntax.py` — extract optimize helper, `slots=True`
- `plugin/rules/match.py` — extract optimize helper, `slots=True`

### Not modified (already frozen)
- `plugin/snapshot.py` — `ViewSnapshot` already `frozen=True`; `slots=True` incompatible with `cached_property`

---

### Task 1: Fix dead code in `ConstraintRule.optimize()`

**Files:**
- Modify: `plugin/rules/constraint.py:62-65`

- [ ] **Step 1: Replace dead `return`/`yield` with clean no-op generator**

In `plugin/rules/constraint.py`, replace:

```python
@override
def optimize(self) -> Generator[Optimizable]:
    return
    yield
```

with:

```python
@override
def optimize(self) -> Generator[Optimizable]:
    """Leaf constraint has no sub-rules to optimize."""
    return
    yield  # noqa: required by Generator protocol for abstract Optimizable
```

- [ ] **Step 2: Verify no lint or type errors**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && uv run --dev mypy -p plugin && uv run --dev ruff check --diff . && uv run --dev ruff format --diff .
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "fix: replace dead code in ConstraintRule.optimize() with clean no-op generator"
```

---

### Task 2: Clean up `_configured_debounce` in listener.py

**Files:**
- Modify: `plugin/listener.py:84-96`

- [ ] **Step 1: Replace hand-rolled dict cache with `@lru_cache` factory**

Reformat `_configured_debounce` and add `_make_debounced` factory:

```python
@lru_cache(maxsize=2)
def _make_debounced[T: Callable](func: T, time_s: float) -> T:
    return debounce(time_s)(func)  # type: ignore[return-value]


def _configured_debounce[T: Callable](func: T) -> T:
    @wraps(func)
    def debounced(*args: Any, **kwargs: Any) -> Any:
        if (time_s := get_merged_plugin_setting("debounce", 0)) > 0:
            return _make_debounced(func, time_s)(*args, **kwargs)
        return func(*args, **kwargs)

    return debounced  # type: ignore[return-value]
```

`_make_debounced` goes BEFORE `_configured_debounce` in the file (but after the `_guarantee_primary_view` function). The import of `lru_cache` from `functools` is already present.

- [ ] **Step 2: Verify via `make ci-check`**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && make ci-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "refactor: replace _configured_debounce dict cache with @lru_cache factory"
```

---

### Task 3: Convert `G` class to module-level instance

**Files:**
- Modify: `plugin/shared.py`

- [ ] **Step 1: Replace class-with-class-vars pattern with `@dataclass` + instance**

Current `plugin/shared.py`:

```python
type DroppedRules = list[Optimizable]

DroppedRulesCollection = WindowKeyedDict[DroppedRules]
SyntaxRuleCollections = WindowKeyedDict[SyntaxRuleCollection]


class G:
    """This class holds "G"lobal variables as its class variables."""

    startup_views: set[sublime.View] = set()

    syntax_rule_collections = SyntaxRuleCollections()

    dropped_rules_collection = DroppedRulesCollection()

    @classmethod
    def is_plugin_ready(cls, window: sublime.Window) -> bool:
        return bool(get_merged_plugin_settings(window=window) and cls.syntax_rule_collections.get(window))
```

Replace with:

```python
from dataclasses import dataclass, field

type DroppedRules = list[Optimizable]

DroppedRulesCollection = WindowKeyedDict[DroppedRules]
SyntaxRuleCollections = WindowKeyedDict[SyntaxRuleCollection]


@dataclass
class _GlobalState:
    startup_views: set[sublime.View] = field(default_factory=set)
    syntax_rule_collections: SyntaxRuleCollections = field(default_factory=SyntaxRuleCollections)
    dropped_rules_collection: DroppedRulesCollection = field(default_factory=DroppedRulesCollection)

    def is_plugin_ready(self, window: sublime.Window) -> bool:
        return bool(get_merged_plugin_settings(window=window) and self.syntax_rule_collections.get(window))


G = _GlobalState()
```

Add `from dataclasses import dataclass, field` to the top imports if needed.

- [ ] **Step 2: Verify no lint or type errors**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && make ci-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "refactor: convert G class to module-level @dataclass instance"
```

---

### Task 4: Python 3.14 minor touches

**Files:**
- Modify: `plugin/cache.py:1-6`
- Modify: `plugin/types.py:102`

- [ ] **Step 1: Remove private `_lru_cache_wrapper` import from cache.py**

Current `plugin/cache.py`:

```python
from functools import _lru_cache_wrapper
from functools import lru_cache
```

Replace with (no private import):

```python
from functools import lru_cache
```

And change `_cached_functions` type from `set[_lru_cache_wrapper]` to `set[Callable]`:

```python
_cached_functions: set[Callable] = set()
```

Add `from collections.abc import Callable` to the imports at the top.

- [ ] **Step 2: Tighten `WindowKeyedDict.__contains__` from `Any` to `WindowIdAble`**

In `plugin/types.py`, change:

```python
def __contains__(self, key: Any) -> bool:
```

to:

```python
def __contains__(self, key: object) -> bool:
```

(Use `object` instead of `Any` — `WindowIdAble` would make `__contains__` reject valid runtime lookups like `view.window()` which isn't `WindowIdAble` but is handled by `_to_window_id`. Using `object` signals that we accept any type and convert internally.)

- [ ] **Step 3: Verify via `make ci-check`**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && make ci-check
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "chore: remove private functools import, tighten __contains__ signature"
```

---

### Task 5: Extract optimize-filter-optimize pattern

**Files:**
- Create: `plugin/rules/_optimize.py`
- Modify: `plugin/rules/syntax.py:93-105`
- Modify: `plugin/rules/match.py:54-64`

- [ ] **Step 1: Create `plugin/rules/_optimize.py` with shared helper**

```python
from collections.abc import Generator

from ..types import Optimizable


def sift_optimizable[T: Optimizable](rules: tuple[T, ...]) -> tuple[list[Optimizable], tuple[T, ...]]:
    """Filter droppable rules and recurse-optimize survivors.

    Yields no items directly. Returns a tuple of (dropped_rules, surviving_rules).
    """
    dropped: list[Optimizable] = []
    survivors: list[T] = []
    for rule in rules:
        if rule.is_droppable():
            dropped.append(rule)
            continue
        dropped.extend(rule.optimize())
        if rule.is_droppable():
            dropped.append(rule)
            continue
        survivors.append(rule)
    return dropped, tuple(survivors)
```

- [ ] **Step 2: Update `SyntaxRuleCollection.optimize()`**

In `plugin/rules/syntax.py`, add import at top:

```python
from ._optimize import sift_optimizable
```

Replace `SyntaxRuleCollection.optimize()` body:

```python
@override
def optimize(self) -> Generator[Optimizable]:
    dropped, self.rules = sift_optimizable(self.rules)
    yield from dropped
```

- [ ] **Step 3: Update `MatchRule.optimize()`**

In `plugin/rules/match.py`, add import at top:

```python
from ._optimize import sift_optimizable
```

Replace `MatchRule.optimize()` body:

```python
@override
def optimize(self) -> Generator[Optimizable]:
    dropped, self.rules = sift_optimizable(self.rules)
    yield from dropped
```

- [ ] **Step 4: Verify via `make ci-check`**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && make ci-check
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "refactor: extract shared sift_optimizable() from duplicated optimize loops"
```

---

### Task 6: Add `slots=True` to remaining dataclasses

**Files:**
- Modify: `plugin/rules/constraint.py:48`
- Modify: `plugin/rules/syntax.py:20-22`
- Modify: `plugin/rules/match.py:38-44`

Changes per file:

`plugin/rules/constraint.py` line 48:
```python
@dataclass
class ConstraintRule(Optimizable):
```
→
```python
@dataclass(slots=True, frozen=True)
class ConstraintRule(Optimizable):
```

`plugin/rules/syntax.py` line 21:
```python
@dataclass
class SyntaxRule(Optimizable):
```
→
```python
@dataclass(slots=True)
class SyntaxRule(Optimizable):
```

`plugin/rules/syntax.py` line 86:
```python
@dataclass
class SyntaxRuleCollection(Optimizable):
```
→
```python
@dataclass(slots=True)
class SyntaxRuleCollection(Optimizable):
```

`plugin/rules/match.py` line 38:
```python
@dataclass
class MatchRule(Optimizable):
```
→
```python
@dataclass(slots=True)
class MatchRule(Optimizable):
```

- [ ] **Step 1: Add `slots=True` to `ConstraintRule` (+ frozen), `SyntaxRule`, `SyntaxRuleCollection`, `MatchRule`**

Apply the `@dataclass(slots=True)` changes from above.

- [ ] **Step 2: Verify via `make ci-check`**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && make ci-check
```

Expected: No errors. (If mypy flags `__dict__` access on a slotted class, that's expected and would need checking.)

- [ ] **Step 3: Commit**

```bash
cd "D:\Repo\ST-AutoSetSyntax" && git add -A && git commit -m "perf: add slots=True to dataclasses, frozen=True on ConstraintRule"
```
