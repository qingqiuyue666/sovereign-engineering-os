"""
P0-9 phase 1 — RecoverySessionHost.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

A bounded in-process owner of a live `SessionOrchestrator` instance
and a pre-built `RecoveryGate`. This is the smallest correct runtime
boundary at which `restore_task_from_snapshot` is meaningful: a
restored task lives in the host-owned orchestrator's `_tasks` dict
and remains available for follow-on admission against the same
instance for the host's lifetime.

P0-8 proved that a one-shot `recovery_cli restore` subcommand would
be ephemeral and misleading — restored orchestrator memory
disappears when the CLI process exits. P0-9 introduces a host that
keeps the orchestrator alive across restore + admission so the
restore has a continuable runtime effect.

This module is NOT a daemon, web server, async runtime, queue, IPC,
scheduler, or background worker. It is a synchronous in-process
owner of three references and a closed flag.

Out of scope (delegated):
- DB connection ownership: caller responsibility (release via
  ``close_callback``).
- Repository / service wiring: caller responsibility.
- Recovery policy: lives in `RecoveryGate` / `TaskRecoveryClassifier`.
- Restore safety: lives in
  `SignablePathOrchestrator.restore_task_from_snapshot` (the gate's
  final authority).
- Artifact integrity: lives in `StageArtifactExistenceResolver`.
- Schema, migration, or audit ``record_type`` additions: not
  introduced here.

This class does not import `SignablePathOrchestrator`. The owned
runtime is protocol-typed via `SessionOrchestrator` so the host
stays a thin runtime boundary rather than a wiring graph.
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol

from kernel.lifecycle.recovery_gate import RecoveryGate, RecoveryGateResult
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    TaskLifecycleSnapshot,
)


class RecoverySessionHostClosed(RuntimeError):
    """Raised when a public `RecoverySessionHost` operation is
    attempted after `close()` has run.

    Subclass of `RuntimeError` so existing broad-except sites do not
    need to learn a new exception type to fail closed; specific
    callers can still catch this class directly to distinguish
    closed-host errors from other runtime conditions.
    """


class SessionOrchestrator(Protocol):
    """Minimal protocol the host requires of the owned orchestrator.

    Avoids a hard import of `SignablePathOrchestrator` so this module
    does not bind to runtime composition. Concrete callers pass
    their `SignablePathOrchestrator` instance directly; the gate's
    `restore_if_allowed` keeps final authority over restore safety
    via `restore_task_from_snapshot`.
    """

    def restore_task_from_snapshot(
        self,
        *,
        snapshot: TaskLifecycleSnapshot,
        recovery_class: RecoveryClass,
    ) -> None: ...

    def current_stage(self, task_id: str) -> Optional[Stage]: ...


class RecoverySessionHost:
    """Bounded in-process owner of a live orchestrator + RecoveryGate.

    Constructor contract:
    - ``recovery_gate``: a fully composed `RecoveryGate` (e.g. built
      via `build_standard_recovery_gate`). The host does not
      construct gates.
    - ``orchestrator``: a live `SessionOrchestrator` instance the
      caller has already wired against the durable substrate. The
      host does not construct orchestrators, repositories, services,
      or DB connections.
    - ``close_callback``: optional zero-arg callable invoked exactly
      once on the first `close()`. Typical use is releasing the
      caller-owned SQLite connection. Exceptions from the callback
      propagate; the host is still marked closed so a subsequent
      `close()` is a no-op.

    Public surface:
    - ``orchestrator`` (property): the owned live instance, for
      callers that want to continue admission after restore.
    - ``evaluate_task(task_id)``: read-only verdict via the gate.
    - ``restore_task(task_id)``: gate's `restore_if_allowed` against
      the owned orchestrator. Restore exceptions
      (`OrchestratorRejected`, integrity-guard failures inside
      `restore_task_from_snapshot`) propagate unchanged.
    - ``current_stage(task_id)``: pass-through to the orchestrator.
    - ``close()``: idempotent host shutdown.
    - ``closed`` (property): boolean state.

    All public operations except `close()` and `closed` raise
    `RecoverySessionHostClosed` after the host has been closed. The
    host writes no durable rows itself; any durable side effect is
    the responsibility of the wrapped orchestrator's existing
    admission boundary (`KernelUnitOfWork`).
    """

    __slots__ = (
        "_gate",
        "_orchestrator",
        "_close_callback",
        "_closed",
    )

    def __init__(
        self,
        *,
        recovery_gate: RecoveryGate,
        orchestrator: SessionOrchestrator,
        close_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._gate = recovery_gate
        self._orchestrator = orchestrator
        self._close_callback = close_callback
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _check_open(self) -> None:
        if self._closed:
            raise RecoverySessionHostClosed(
                "RecoverySessionHost is closed"
            )

    @property
    def orchestrator(self) -> SessionOrchestrator:
        self._check_open()
        return self._orchestrator

    def evaluate_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.evaluate(task_id)

    def restore_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.restore_if_allowed(
            task_id=task_id,
            orchestrator=self._orchestrator,
        )

    def current_stage(self, task_id: str) -> Optional[Stage]:
        self._check_open()
        return self._orchestrator.current_stage(task_id)

    def close(self) -> None:
        if self._closed:
            return
        # Mark closed before invoking the callback so a callback
        # exception still leaves the host closed and a subsequent
        # close() is a no-op (callback runs exactly once even on
        # error, never twice).
        self._closed = True
        if self._close_callback is not None:
            self._close_callback()
