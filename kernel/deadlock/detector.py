"""Deterministic wait-for graph deadlock detector."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator
import threading
import time

from kernel.audit.trail import audit
from kernel.errors.hierarchy import DeadlockDetectedError

__all__ = ["DeadlockDetector", "LockGraph", "LockNode"]


@dataclass
class LockNode:
    name: str
    holder_id: str | None = None
    waiter_ids: set[str] = field(default_factory=set)
    acquired_at: float | None = None
    timeout_seconds: float | None = None


class LockGraph:
    """Thread-safe lock ownership and wait-for graph."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self._nodes: dict[str, LockNode] = {}
        self._lock = threading.RLock()
        self._clock = clock

    def register(self, name: str, *, timeout_seconds: float | None = None) -> None:
        _validate_name(name)
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise DeadlockDetectedError("timeout_seconds_must_be_positive")
        with self._lock:
            node = self._nodes.get(name)
            if node is None:
                self._nodes[name] = LockNode(name=name, timeout_seconds=timeout_seconds)
            elif timeout_seconds is not None:
                node.timeout_seconds = timeout_seconds

    def mark_acquired(self, name: str, holder_id: str) -> None:
        _validate_name(holder_id, field="holder_id")
        with self._lock:
            self.register(name)
            node = self._nodes[name]
            node.holder_id = holder_id
            node.waiter_ids.discard(holder_id)
            node.acquired_at = self._clock()

    def mark_waiting(self, name: str, waiter_id: str) -> None:
        _validate_name(waiter_id, field="waiter_id")
        with self._lock:
            self.register(name)
            self._nodes[name].waiter_ids.add(waiter_id)

    def release(self, name: str, *, holder_id: str | None = None) -> None:
        with self._lock:
            node = self._nodes.get(name)
            if node is None:
                return
            if holder_id is not None and node.holder_id != holder_id:
                raise DeadlockDetectedError("lock_release_holder_mismatch")
            node.holder_id = None
            node.acquired_at = None

    def clear_waiter(self, name: str, waiter_id: str) -> None:
        with self._lock:
            node = self._nodes.get(name)
            if node is not None:
                node.waiter_ids.discard(waiter_id)

    def detect_cycle(self) -> tuple[str, ...]:
        with self._lock:
            edges = self._lock_edges()
        return _first_cycle(edges)

    def timed_out_locks(self) -> tuple[str, ...]:
        now = self._clock()
        timed_out: list[str] = []
        with self._lock:
            for name in sorted(self._nodes):
                node = self._nodes[name]
                if node.holder_id is None or node.acquired_at is None or node.timeout_seconds is None:
                    continue
                if now - node.acquired_at > node.timeout_seconds:
                    timed_out.append(name)
        return tuple(timed_out)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                name: {
                    "holder_id": node.holder_id,
                    "waiter_ids": sorted(node.waiter_ids),
                    "timeout_seconds": node.timeout_seconds,
                }
                for name, node in sorted(self._nodes.items())
            }

    def _lock_edges(self) -> dict[str, set[str]]:
        held_by_thread: dict[str, set[str]] = {}
        for lock_name, node in self._nodes.items():
            if node.holder_id is not None:
                held_by_thread.setdefault(node.holder_id, set()).add(lock_name)
        edges: dict[str, set[str]] = {}
        for waited_lock, node in self._nodes.items():
            for waiter_id in node.waiter_ids:
                for held_lock in held_by_thread.get(waiter_id, set()):
                    if held_lock != waited_lock:
                        edges.setdefault(waited_lock, set()).add(held_lock)
        return edges


class DeadlockDetector:
    """Fail-closed facade around LockGraph."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self.graph = LockGraph(clock=clock)

    def mark_acquired(self, lock_name: str, owner_id: str, *, timeout_seconds: float | None = None) -> None:
        self.graph.register(lock_name, timeout_seconds=timeout_seconds)
        self.graph.mark_acquired(lock_name, owner_id)
        self.assert_clear()

    def mark_waiting(self, lock_name: str, owner_id: str) -> None:
        self.graph.mark_waiting(lock_name, owner_id)
        self.assert_clear()

    def release(self, lock_name: str, *, owner_id: str | None = None) -> None:
        self.graph.release(lock_name, holder_id=owner_id)

    def detect_deadlock(self) -> tuple[str, ...]:
        return self.graph.detect_cycle()

    def assert_clear(self) -> None:
        cycle = self.graph.detect_cycle()
        if cycle:
            audit("deadlock.cycle_detected", cycle=list(cycle))
            raise DeadlockDetectedError("deadlock_detected:" + "->".join(cycle))
        timed_out = self.graph.timed_out_locks()
        if timed_out:
            audit("deadlock.timeout_detected", locks=list(timed_out))
            raise DeadlockDetectedError("lock_timeout:" + ",".join(timed_out))

    @contextmanager
    def acquire(
        self,
        lock_name: str,
        *,
        owner_id: str,
        timeout_seconds: float | None = None,
    ) -> Generator[None, None, None]:
        self.graph.register(lock_name, timeout_seconds=timeout_seconds)
        snapshot = self.graph.snapshot()
        node = snapshot.get(lock_name)
        if isinstance(node, dict) and node.get("holder_id") not in (None, owner_id):
            self.graph.mark_waiting(lock_name, owner_id)
            self.assert_clear()
            raise DeadlockDetectedError(f"lock_unavailable:{lock_name}")
        self.graph.mark_acquired(lock_name, owner_id)
        try:
            self.assert_clear()
            yield
        finally:
            self.graph.release(lock_name, holder_id=owner_id)
            self.graph.clear_waiter(lock_name, owner_id)


def _first_cycle(edges: dict[str, set[str]]) -> tuple[str, ...]:
    visited: set[str] = set()
    stack: list[str] = []
    in_stack: set[str] = set()

    def dfs(node: str) -> tuple[str, ...]:
        visited.add(node)
        in_stack.add(node)
        stack.append(node)
        for next_node in sorted(edges.get(node, ())):
            if next_node not in visited:
                found = dfs(next_node)
                if found:
                    return found
            elif next_node in in_stack:
                index = stack.index(next_node)
                return tuple(stack[index:] + [next_node])
        stack.pop()
        in_stack.remove(node)
        return ()

    for node in sorted(edges):
        if node not in visited:
            found = dfs(node)
            if found:
                return found
    return ()


def _validate_name(value: str, *, field: str = "lock_name") -> None:
    if not isinstance(value, str) or not value:
        raise DeadlockDetectedError(f"{field}_required")
