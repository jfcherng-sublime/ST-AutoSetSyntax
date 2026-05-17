# Codebase Polish: Immutability, Dead Code Removal, and Modernization

Date: 2026-05-17

## Summary

Incremental improvements to the AutoSetSyntax plugin codebase: fix dead code, add `slots=True` / `frozen=True` to dataclasses, extract duplicated optimize pattern, clean up a caching pattern, convert the global state holder to a proper instance, and apply minor Python modernizations.

## Changes

### 1. Fix dead code in `ConstraintRule.optimize()`

**File:** `plugin/rules/constraint.py`

The `optimize()` method has unreachable `yield` after `return`. Replace with a clean no-op generator pattern, with a comment explaining the `yield` is required by the `Generator` protocol.

### 2. Slots and immutability for dataclasses

| Dataclass | File | Change |
|---|---|---|
| `ConstraintRule` | `constraint.py` | `slots=True, frozen=True` |
| `SyntaxRule` | `syntax.py` | `slots=True` |
| `SyntaxRuleCollection` | `syntax.py` | `slots=True` |
| `MatchRule` | `match.py` | `slots=True` |

`ViewSnapshot` is already frozen. The three kept-mutable ones (`SyntaxRule`, `SyntaxRuleCollection`, `MatchRule`) self-mutate during `optimize()`; full immutability requires restructuring the optimize system to return new instances, left for follow-up.

### 3. Extract duplicated optimize-filter-optimize pattern

**New file:** `plugin/rules/_optimize.py`

The same `sift` loop appears in `SyntaxRuleCollection.optimize()` and `MatchRule.optimize()` — iterate rules, check droppability, recursively optimize, check again, collect survivors. Extract into a shared `sift_optimizable()` function:

```python
def sift_optimizable[T: Optimizable](rules: tuple[T, ...]) -> tuple[list[Optimizable], tuple[T, ...]]
```

Returns `(dropped, survivors)`. Callers yield from `dropped` and assign survivors.

### 4. Clean up `_configured_debounce`

**File:** `plugin/listener.py`

Replace the hand-rolled dict-based cache with `@lru_cache` on a factory helper:

- Current: closure dict keyed by float, manual `_cache.clear()` on change
- New: `_make_debounced(func, time_s)` with `@lru_cache(maxsize=2)`, called from `_configured_debounce`. Cache invalidation handled by existing `clear_all_cached_functions()`.

### 5. Convert `G` class to module-level instance

**File:** `plugin/shared.py`

Replace class-as-namespace pattern with a frozen `@dataclass` instantiated as module-level `G`. The import API (`from .shared import G`) stays identical. Enables clean reset for tests.

### 6. Python 3.14 minor touches

- **`cache.py`:** Remove private `_lru_cache_wrapper` import; track cached functions via `set[Callable]` instead.
- **`types.py`:** Tighten `WindowKeyedDict.__contains__` arg from `Any` to `WindowIdAble`.
- Remove spurious `@override` on `__init__` methods in constraint implementations (e.g., `IsExtensionConstraint.__init__`), since `__init__` isn't overriding an abstract method.
