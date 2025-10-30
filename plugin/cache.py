from __future__ import annotations

from collections.abc import Callable
from functools import _lru_cache_wrapper, lru_cache
from typing import Any, cast

_cached_functions: set[_lru_cache_wrapper] = set()


def clearable_lru_cache[T: Callable](*args: Any, **kwargs: Any) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return cast(T, wrapped)

    return decorator


def clear_all_cached_functions() -> None:
    for func in _cached_functions:
        func.cache_clear()
