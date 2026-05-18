"""Dry-run watchdog deadline tracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import time

from kernel.audit.trail import audit
from kernel.errors.hierarchy import WatchdogExpiredError

__all__ = ["Watchdog", "WatchdogSnapshot"]


@dataclass(frozen=True)
class WatchdogSnapshot:
    name: str
    deadline_seconds: float
    seconds_since_feed: float
    expired: bool
    observed_at: str
    dry_run_only: bool = True

    def deterministic_material(self) -> dict[str, object]:
        return {
            "deadline_seconds": self.deadline_seconds,
            "dry_run_only": self.dry_run_only,
            "expired": self.expired,
            "name": self.name,
        }


class Watchdog:
    """Manual watchdog checker that never kills the process."""

    def __init__(
        self,
        *,
        deadline_seconds: float,
        name: str = "watchdog",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if deadline_seconds <= 0:
            raise WatchdogExpiredError("deadline_seconds_must_be_positive")
        if not isinstance(name, str) or not name:
            raise WatchdogExpiredError("watchdog_name_required")
        self.deadline_seconds = float(deadline_seconds)
        self.name = name
        self._clock = clock
        self._last_feed = self._clock()
        self._last_observed_at = _observed_at(None)

    def feed(self, *, observed_at: str | None = None) -> WatchdogSnapshot:
        self._last_feed = self._clock()
        self._last_observed_at = _observed_at(observed_at)
        audit("watchdog.fed", name=self.name)
        return self.snapshot(observed_at=self._last_observed_at)

    def seconds_since_last_feed(self) -> float:
        return max(0.0, self._clock() - self._last_feed)

    def expired(self) -> bool:
        return self.seconds_since_last_feed() > self.deadline_seconds

    def check(self, *, observed_at: str | None = None) -> WatchdogSnapshot:
        snapshot = self.snapshot(observed_at=observed_at)
        if snapshot.expired:
            audit("watchdog.expired", name=self.name, deadline_seconds=self.deadline_seconds)
            raise WatchdogExpiredError(f"watchdog_expired:{self.name}")
        audit("watchdog.ok", name=self.name)
        return snapshot

    def snapshot(self, *, observed_at: str | None = None) -> WatchdogSnapshot:
        observed = _observed_at(observed_at) if observed_at is not None else self._last_observed_at
        return WatchdogSnapshot(
            name=self.name,
            deadline_seconds=self.deadline_seconds,
            seconds_since_feed=self.seconds_since_last_feed(),
            expired=self.expired(),
            observed_at=observed,
        )


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str) or not value:
        raise WatchdogExpiredError("observed_at_must_be_nonempty_string")
    return value
