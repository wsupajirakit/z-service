"""In-process sliding-window rate limiter.

z-service runs as one container, so process memory is the right store; no extra
dependency. Shared by machine keys and the login endpoint.

Keys come from clients (login keys on IP + username), so the table is bounded: keys idle
for a whole window are pruned, and past `max_keys` the least recently used key is
dropped. An attacker who floods new keys mostly evicts their own entries; the per-IP
login limit stops a single client from generating many keys.
"""

import collections
import threading
import time

DEFAULT_MAX_KEYS = 10_000


class SlidingWindow:
    def __init__(self, limit: int, window_s: int, max_keys: int = DEFAULT_MAX_KEYS):
        if limit < 1 or window_s < 1 or max_keys < 1:
            raise ValueError("limit, window_s and max_keys must be >= 1")
        self.limit, self.window_s, self.max_keys = limit, window_s, max_keys
        self._hits: collections.OrderedDict[str, collections.deque[float]] = (
            collections.OrderedDict()
        )
        self._lock = threading.Lock()
        self._pruned_at = 0.0

    def hit(self, key: str, now: float | None = None) -> int | None:
        """Record one request; return seconds to wait when over the limit, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(now)
            hits = self._hits.setdefault(key, collections.deque())
            self._hits.move_to_end(key)  # most recently used last
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, int(hits[0] + self.window_s - now) + 1)
            hits.append(now)
            while len(self._hits) > self.max_keys:
                self._hits.popitem(last=False)
            return None

    def __len__(self) -> int:
        return len(self._hits)

    def _prune(self, now: float) -> None:
        """Drop keys with no hit inside the window; at most once per window."""
        if now - self._pruned_at < self.window_s:
            return
        self._pruned_at = now
        cutoff = now - self.window_s
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]
