"""Slowing down password guessing.

Failed sign-ins are counted per key (email + client address) in memory. This is
per process, which is fine for a small deployment; behind several workers an
attacker gets a few more tries, not unlimited ones.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock


class LoginThrottle:
    def __init__(
        self, max_failures: int = 5, window_seconds: int = 900, clock: Callable = time.monotonic
    ):
        self.max_failures = max_failures
        self.window = window_seconds
        self.clock = clock
        self._failures: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str) -> deque:
        failures = self._failures[key]
        cutoff = self.clock() - self.window
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key)) >= self.max_failures

    def retry_after(self, key: str) -> int:
        with self._lock:
            failures = self._prune(key)
            if len(failures) < self.max_failures:
                return 0
            return max(1, int(failures[0] + self.window - self.clock()))

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key).append(self.clock())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
