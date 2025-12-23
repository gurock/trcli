"""
API Response Cache Module

This module provides a session-scoped caching mechanism for API responses
to reduce redundant API calls and improve performance.

The cache is designed to be:
- Thread-safe
- Session-scoped (per ApiRequestHandler instance)
- Backwards compatible (transparent to existing code)
- Memory-efficient (uses LRU eviction)
"""

from functools import lru_cache
from typing import Any, Tuple, Optional, Callable
from threading import Lock
from beartype.typing import List, Dict


class RequestCache:
    """
    Session-scoped cache for API responses.

    This cache stores API responses during a single command execution session
    to avoid redundant API calls. Each ApiRequestHandler instance should have
    its own cache instance.

    Key features:
    - Automatic cache key generation from endpoint and parameters
    - LRU eviction policy to prevent unbounded memory growth
    - Thread-safe operations
    - Simple invalidation mechanism
    """

    def __init__(self, max_size: int = 512):
        """
        Initialize the request cache.

        Args:
            max_size: Maximum number of cached responses (default: 512)
        """
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._lock = Lock()
        self._hit_count = 0
        self._miss_count = 0

    def _make_cache_key(self, endpoint: str, params: Optional[Tuple] = None) -> str:
        """
        Generate a unique cache key from endpoint and parameters.

        Args:
            endpoint: API endpoint (e.g., "get_cases/123")
            params: Optional tuple of parameters

        Returns:
            String cache key
        """
        if params is None:
            return endpoint

        # Convert params to a sorted tuple to ensure consistent keys
        if isinstance(params, dict):
            params_tuple = tuple(sorted(params.items()))
        elif isinstance(params, (list, tuple)):
            params_tuple = tuple(params)
        else:
            params_tuple = (params,)

        return f"{endpoint}::{params_tuple}"

    def get(self, endpoint: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        Retrieve a cached response.

        Args:
            endpoint: API endpoint
            params: Optional parameters

        Returns:
            Cached response or None if not found
        """
        cache_key = self._make_cache_key(endpoint, params)

        with self._lock:
            if cache_key in self._cache:
                self._hit_count += 1
                return self._cache[cache_key]
            else:
                self._miss_count += 1
                return None

    def set(self, endpoint: str, response: Any, params: Optional[Tuple] = None) -> None:
        """
        Store a response in the cache.

        Args:
            endpoint: API endpoint
            response: Response to cache
            params: Optional parameters
        """
        cache_key = self._make_cache_key(endpoint, params)

        with self._lock:
            # Implement simple LRU: if cache is full, remove oldest entry
            if len(self._cache) >= self.max_size:
                # Remove the first (oldest) item
                first_key = next(iter(self._cache))
                del self._cache[first_key]

            self._cache[cache_key] = response

    def invalidate(self, endpoint: Optional[str] = None, params: Optional[Tuple] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            endpoint: If provided, invalidate only this endpoint.
                     If None, clear entire cache.
            params: Optional parameters to narrow invalidation
        """
        with self._lock:
            if endpoint is None:
                # Clear entire cache
                self._cache.clear()
            else:
                cache_key = self._make_cache_key(endpoint, params)
                if cache_key in self._cache:
                    del self._cache[cache_key]

    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate all cache entries matching a pattern.

        Args:
            pattern: String pattern to match against cache keys
        """
        with self._lock:
            keys_to_delete = [key for key in self._cache if pattern in key]
            for key in keys_to_delete:
                del self._cache[key]

    def get_or_fetch(
        self,
        endpoint: str,
        fetch_func: Callable[[], Tuple[Any, str]],
        params: Optional[Tuple] = None,
        force_refresh: bool = False,
    ) -> Tuple[Any, str]:
        """
        Get cached response or fetch if not cached.

        This is the main method for integrating caching into existing code.
        It transparently handles cache hits/misses and maintains the same
        return signature as the original fetch functions.

        Args:
            endpoint: API endpoint
            fetch_func: Function to call if cache miss (should return (data, error))
            params: Optional parameters for cache key
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Tuple of (data, error_message) matching API call signature
        """
        if not force_refresh:
            cached = self.get(endpoint, params)
            if cached is not None:
                # Return cached result
                return cached

        # Cache miss or force refresh - fetch fresh data
        result = fetch_func()

        # Only cache successful responses (no error)
        data, error = result
        if not error:
            self.set(endpoint, result, params)

        return result

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit_count, miss_count, size, and hit_rate
        """
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total * 100) if total > 0 else 0.0

            return {
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "size": len(self._cache),
                "hit_rate": hit_rate,
            }

    def clear(self) -> None:
        """Clear all cached data and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hit_count = 0
            self._miss_count = 0
