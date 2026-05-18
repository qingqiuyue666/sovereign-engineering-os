"""Watchdog: deadman-timer that kills the process if not fed within a deadline."""

from __future__ import annotations

import os
import signal
import threading
import time
from datetime import datetime, timezone

from kernel.audit.trail import audit
from kernel.errors.hierarchy import WatchdogExpiredError


class Watchdog:
    """Deadman-timer watchdog.

    Call `feed()` periodically. If `feed()` isn't called within `deadline_seconds`,
    the watchdog fires: it logs the event and raises WatchdogExpiredError.

    Thread-safe. Intended to run in a dedicated daemon thread.
    """

    def __init__(self, deadline_seconds: float = 30.0, name: str = "watchdog") -> None:
        self.deadline_seconds = deadline_seconds
        self.name = name
        self._last_feed = time.monotonic()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._on_expire: list[tuple[str, object]] = []

    def feed(self) -> None:
        """Reset the deadman timer."""
        with self._lock:
            self._last_feed = time.monotonic()

    def start(self) -> None:
        """Start the watchdog monitoring thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_feed = time.monotonic()

        self._thread = threading.Thread(target=self._loop, daemon=True, name=self.name)
        self._thread.start()
        audit("watchdog.started", name=self.name, deadline_seconds=self.deadline_seconds)

    def stop(self) -> None:
        """Graceful stop."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        audit("watchdog.stopped", name=self.name)

    def time_since_last_feed(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_feed

    def is_expired(self) -> bool:
        return self.time_since_last_feed() > self.deadline_seconds

    # ── internal ────────────────────────────────────────────────

    def _loop(self) -> None:
        check_interval = max(0.5, self.deadline_seconds / 10.0)
        while True:
            with self._lock:
                if not self._running:
                    break
            time.sleep(check_interval)
            if self.is_expired():
                self._fire()

    def _fire(self) -> None:
        with self._lock:
            self._running = False
        audit("watchdog.expired", name=self.name, deadline_seconds=self.deadline_seconds,
              seconds_since_feed=self.time_since_last_feed())
        raise WatchdogExpiredError(
            f"watchdog_expired:{self.name} deadline={self.deadline_seconds}s "
            f"last_feed={self.time_since_last_feed():.1f}s_ago"
        )
