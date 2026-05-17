from collections.abc import Callable
from functools import lru_cache
from typing import Any

_cached_functions: set[Callable] = set()


def clearable_lru_cache[T: Callable](*args: Any, **kwargs: Any) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return wrapped  # type: ignore[return-value]

    return decorator


def clear_all_cached_functions() -> None:
    for func in _cached_functions:
        func.cache_clear()  # type: ignore[attr-defined]
