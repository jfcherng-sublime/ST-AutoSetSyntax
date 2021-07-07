from functools import lru_cache
from typing import Any, Callable, Set

# specifically, Set[_lru_cache_wrapper]
cached_functions: Set[Callable] = set()


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable:
    def decorator(func: Callable) -> Callable:
        wrapped_func = lru_cache(*args, **kwargs)(func)
        cached_functions.add(wrapped_func)
        return wrapped_func

    return decorator


def clear_all_cached_functions():
    for func in cached_functions:
        func.cache_clear()  # type: ignore
