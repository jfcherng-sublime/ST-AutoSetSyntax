from functools import _lru_cache_wrapper
from functools import lru_cache
from typing import Any, Callable, Set

cached_functions: Set[_lru_cache_wrapper] = set()


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        wrapped = lru_cache(*args, **kwargs)(func)
        cached_functions.add(wrapped)
        return wrapped

    return decorator


def clear_all_cached_functions():
    for func in cached_functions:
        func.cache_clear()
