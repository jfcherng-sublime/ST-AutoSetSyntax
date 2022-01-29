from functools import _lru_cache_wrapper
from functools import lru_cache
from typing import Any, Callable, Set, TypeVar, cast

AnyCallable = TypeVar("AnyCallable", bound=Callable[..., Any])

cached_functions: Set[_lru_cache_wrapper] = set()


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable[[AnyCallable], AnyCallable]:
    def decorator(func: AnyCallable) -> AnyCallable:
        wrapped = lru_cache(*args, **kwargs)(func)
        cached_functions.add(wrapped)
        return cast(AnyCallable, wrapped)

    return decorator


def clear_all_cached_functions():
    for func in cached_functions:
        func.cache_clear()
