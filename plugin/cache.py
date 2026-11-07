from collections.abc import Callable
from functools import lru_cache
from typing import Any
from typing import cast

_cached_functions: set[Callable] = set()
_clearers: list[Callable[[], object]] = []


def clearable_lru_cache[T: Callable](*args: Any, **kwargs: Any) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return cast(T, wrapped)

    return decorator


def register_cache_clearer(clear: Callable[[], object]) -> None:
    """Have `clear_all_cached_functions()` also call `clear`, for a cache that isn't an `lru_cache`."""
    _clearers.append(clear)


def clear_all_cached_functions() -> None:
    for clear in _clearers:
        clear()
    for func in _cached_functions:
        func.cache_clear()  # type: ignore[attr-defined]
