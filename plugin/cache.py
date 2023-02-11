from functools import _lru_cache_wrapper, lru_cache
from typing import Any, Callable, Set, TypeVar, cast

_cached_functions: Set[_lru_cache_wrapper] = set()

_T_Callable = TypeVar("_T_Callable", bound=Callable[..., Any])


def clearable_lru_cache(*args: Any, **kwargs: Any) -> Callable[[_T_Callable], _T_Callable]:
    def decorator(func: _T_Callable) -> _T_Callable:
        wrapped = lru_cache(*args, **kwargs)(func)
        _cached_functions.add(wrapped)
        return cast(_T_Callable, wrapped)

    return decorator


def clear_all_cached_functions() -> None:
    for func in _cached_functions:
        func.cache_clear()
