"""Tests for the clearable LRU cache wrapper."""

from plugin.cache import clear_all_cached_functions
from plugin.cache import clearable_lru_cache


class TestClearableLruCache:
    def test_basic_caching(self):
        call_count = 0

        @clearable_lru_cache()
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert call_count == 1
        # Second call with same args should use cache
        assert add(1, 2) == 3
        assert call_count == 1

    def test_clear_all_caches(self):
        call_count = 0

        @clearable_lru_cache()
        def square(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * x

        assert square(4) == 16
        assert call_count == 1
        # Clear all cached functions
        clear_all_cached_functions()
        assert square(4) == 16
        assert call_count == 2  # recomputed
