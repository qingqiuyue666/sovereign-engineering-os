"""Daemon lifecycle management."""

from __future__ import annotations

from kernel.daemon.supervisor import Supervisor
from kernel.daemon.watchdog import Watchdog

__all__ = ["Supervisor", "Watchdog"]
