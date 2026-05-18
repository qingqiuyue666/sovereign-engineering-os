"""Deadlock detection via wait-for graph analysis."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator

from kernel.audit.trail import audit
from kernel.errors.hierarchy import DeadlockDetectedError

__all__ = ["DeadlockDetector", "LockHandle", "LockGraph"]


@dataclass
class LockNode:
    name: str
    holder_thread_id: int | None = None
    waiters: set[int] = field(default_factory=set)
    acquired_at: float = 0.0
    timeout_seconds: float = 30.0


class LockGraph:
    """Thread-safe wait-for graph for deadlock detection."""

    def __init__(self) -> None:
        self._nodes: dict[str, LockNode] = {}
        self._lock = threading.Lock()

    def register(self, name: str, timeout_seconds: float = 30.0) -> LockNode:
        with self._lock:
            if name not in self._nodes:
                self._nodes[name] = LockNode(name=name, timeout_seconds=timeout_seconds)
            return self._nodes[name]

    def acquire(self, name: str, thread_id: int) -> None:
        with self._lock:
            node = self._nodes.get(name)
            if node is None:
                return
            node.holder_thread_id = thread_id
            node.acquired_at = time.monotonic()
            node.waiters.discard(thread_id)

    def release(self, name: str) -> None:
        with self._lock:
            node = self._nodes.get(name)
            if node is None:
                return
            node.holder_thread_id = None
            node.acquired_at = 0.0

    def add_waiter(self, name: str, thread_id: int) -> None:
        with self._lock:
            node = self._nodes.get(name)
            if node is None:
                return
            node.waiters.add(thread_id)

    def detect_cycle(self) -> list[str] | None:
        """Return the first detected cycle (lock names) or None."""
        with self._lock:
            # Build wait-for edges: if thread T holds A and waits for B, edge B→A
            edges: dict[str, str] = {}
            for name, node in self._nodes.items():
                if node.holder_thread_id is not None:
                    for waiter_tid in node.waiters:
                        # Find what lock this waiter holds
                        for other_name, other_node in self._nodes.items():
                            if other_node.holder_thread_id == waiter_tid and other_name != name:
                                edges[other_name] = name

            # DFS cycle detection
            visited: set[str] = set()
            in_stack: set[str] = set()
            path: list[str] = []

            def dfs(node: str) -> bool:
                visited.add(node)
                in_stack.add(node)
                path.append(node)
                neighbor = edges.get(node)
                if neighbor:
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in in_stack:
                        # Found cycle — trim path to cycle
                        idx = path.index(neighbor)
                        path[:] = path[idx:]
                        path.append(neighbor)
                        return True
                path.pop()
                in_stack.discard(node)
                return False

            for node_name in self._nodes:
                if node_name not in visited:
                    if dfs(node_name):
                        return path

            return None

    def check_timeouts(self) -> list[str]:
        """Return names of locks held beyond their timeout."""
        now = time.monotonic()
        timed_out: list[str] = []
        with self._lock:
            for name, node in self._nodes.items():
                if node.holder_thread_id is not None and node.acquired_at > 0:
                    if now - node.acquired_at > node.timeout_seconds:
                        timed_out.append(name)
        return timed_out


class LockHandle:
    """RAII handle returned by DeadlockDetector.acquire()."""

    def __init__(self, detector: DeadlockDetector, name: str) -> None:
        self._detector = detector
        self._name = name
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._detector.release(self._name)
            self._released = True

    def __enter__(self) -> LockHandle:
        return self

    def __exit__(self, *args: object) -> None:
        self.release()


class DeadlockDetector:
    """Global deadlock detection service.

    Usage:
        detector = DeadlockDetector()
        with detector.acquire("resource_x", timeout_seconds=10.0):
            do_work()
    """

    def __init__(self) -> None:
        self._graph = LockGraph()
        self._check_interval_seconds = 5.0
        self._monitor_thread: threading.Thread | None = None
        self._running = False

    @contextmanager
    def acquire(self, name: str, timeout_seconds: float = 30.0) -> Generator[LockHandle, None, None]:
        """Acquire a named lock with deadlock detection. Context manager."""
        thread_id = threading.get_ident()
        self._graph.register(name, timeout_seconds)

        # Check for existing deadlocks before acquiring
        cycle = self._graph.detect_cycle()
        if cycle:
            audit("deadlock.cycle_detected", cycle=cycle)
            raise DeadlockDetectedError(f"deadlock_detected:cycle={cycle}")

        # Check lock timeouts
        timed_out = self._graph.check_timeouts()
        if timed_out:
            audit("deadlock.lock_timeout", locks=timed_out)
            raise DeadlockDetectedError(f"lock_timeout:{timed_out}")

        # Wait with timeout
        deadline = time.monotonic() + timeout_seconds
        acquired = False
        while time.monotonic() < deadline:
            self._graph.add_waiter(name, thread_id)
            # Attempt acquisition
            node = self._graph._nodes.get(name)
            if node and node.holder_thread_id is None:
                self._graph.acquire(name, thread_id)
                acquired = True
                break
            time.sleep(0.01)

        if not acquired:
            self._graph.release(name)
            audit("deadlock.acquire_timeout", lock=name, timeout_seconds=timeout_seconds)
            raise DeadlockDetectedError(f"acquire_timeout:{name} timeout={timeout_seconds}s")

        handle = LockHandle(self, name)
        try:
            yield handle
        finally:
            handle.release()

    def release(self, name: str) -> None:
        self._graph.release(name)

    def start_monitor(self) -> None:
        """Start background deadlock monitor thread."""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="deadlock-monitor")
        self._monitor_thread.start()
        audit("deadlock.monitor_started")

    def stop_monitor(self) -> None:
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        audit("deadlock.monitor_stopped")

    def _monitor_loop(self) -> None:
        while self._running:
            time.sleep(self._check_interval_seconds)
            cycle = self._graph.detect_cycle()
            if cycle:
                audit("deadlock.monitor_cycle_detected", cycle=cycle)

            timed_out = self._graph.check_timeouts()
            for lock_name in timed_out:
                audit("deadlock.monitor_lock_timeout", lock=lock_name)
