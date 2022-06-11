from functools import _lru_cache_wrapper
from functools import lru_cache
from typing import Any, Callable, Set, TypeVar, cast

T_AnyCallable = TypeVar("T_AnyCallable", bound=Callable[..., Any])

_cached_functions: Set[_lru_cache_wrapper] = set()


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable[[T_AnyCallable], T_AnyCallable]:
    def decorator(func: T_AnyCallable) -> T_AnyCallable:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return cast(T_AnyCallable, wrapped)

    return decorator


def clear_all_cached_functions():
    for func in _cached_functions:
        func.cache_clear()
