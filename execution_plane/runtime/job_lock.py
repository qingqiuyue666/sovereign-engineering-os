"""Named in-process job locks."""

from __future__ import annotations

from threading import Lock


class JobLockRegistry:
    def __init__(self) -> None:
        self._registry_lock = Lock()
        self._locks: dict[str, Lock] = {}

    def lock_for(self, key: str) -> Lock:
        with self._registry_lock:
            if key not in self._locks:
                self._locks[key] = Lock()
            return self._locks[key]
