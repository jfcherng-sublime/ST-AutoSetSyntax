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

    def test_different_args_uncached(self):
        call_count = 0

        @clearable_lru_cache()
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert call_count == 1
        assert add(2, 3) == 5
        assert call_count == 2

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

    def test_selective_clear(self):
        """clear_all_cached_functions clears ALL decorated functions."""
        count_a = 0
        count_b = 0

        @clearable_lru_cache()
        def fn_a(x: int) -> int:
            nonlocal count_a
            count_a += 1
            return x + 1

        @clearable_lru_cache()
        def fn_b(x: int) -> int:
            nonlocal count_b
            count_b += 1
            return x * 2

        assert fn_a(1) == 2
        assert fn_b(1) == 2
        assert count_a == 1
        assert count_b == 1

        # Second calls should be cached
        assert fn_a(1) == 2
        assert fn_b(1) == 2
        assert count_a == 1
        assert count_b == 1

        # Clear all
        clear_all_cached_functions()

        # Both should recompute
        assert fn_a(1) == 2
        assert fn_b(1) == 2
        assert count_a == 2
        assert count_b == 2

    def test_maxsize_passthrough(self):
        call_count = 0

        @clearable_lru_cache(maxsize=2)
        def get(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        get(1)
        get(2)
        assert call_count == 2
        # 3rd call with new arg evicts oldest (1)
        get(3)
        assert call_count == 3
        # 1 was evicted, so it recomputes
        get(1)
        assert call_count == 4
