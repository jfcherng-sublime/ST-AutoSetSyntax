from functools import _lru_cache_wrapper, lru_cache
from typing import Any, Callable, Set, cast

from .types import T_Callable

_cached_functions: Set[_lru_cache_wrapper] = set()


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable[[T_Callable], T_Callable]:
    def decorator(func: T_Callable) -> T_Callable:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return cast(T_Callable, wrapped)

    return decorator


def clear_all_cached_functions():
    for func in _cached_functions:
        func.cache_clear()
