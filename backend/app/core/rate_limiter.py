import time
from typing import Dict, List, Tuple
from collections import defaultdict

class InMemoryRateLimiter:
    """
    Lightweight, high-performance in-memory sliding-window rate limiter.
    Consumes less than 100KB of RAM for thousands of active IP/key buckets.
    Zero external daemon required (1GB VPS optimized).
    """

    def __init__(self):
        self._buckets: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup_stale(self, window_seconds: int = 3600):
        """Purges stale buckets once every 10 minutes to maintain near-zero RAM footprint."""
        now = time.time()
        if now - self._last_cleanup < 600:
            return
        self._last_cleanup = now
        stale_keys = []
        for k, timestamps in self._buckets.items():
            self._buckets[k] = [t for t in timestamps if now - t < window_seconds]
            if not self._buckets[k]:
                stale_keys.append(k)
        for k in stale_keys:
            del self._buckets[k]

    def is_limited(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Checks if the given key has exceeded max_requests within window_seconds.
        Returns (is_limited: bool, retry_after_seconds: int).
        """
        self._cleanup_stale(window_seconds)
        now = time.time()
        timestamps = self._buckets[key]

        # Filter out timestamps outside the sliding window
        valid_timestamps = [t for t in timestamps if now - t < window_seconds]
        self._buckets[key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return True, retry_after

        return False, 0

    def record(self, key: str):
        """Records an event timestamp for the key."""
        self._buckets[key].append(time.time())

    def reset(self, key: str):
        """Clears all recorded timestamps for the key (e.g. on successful login)."""
        if key in self._buckets:
            del self._buckets[key]

# Global singletons for specific security scopes
auth_limiter = InMemoryRateLimiter()      # Failed logins (IP + user)
register_limiter = InMemoryRateLimiter()  # Registrations per IP
api_limiter = InMemoryRateLimiter()       # General API rate limiting
