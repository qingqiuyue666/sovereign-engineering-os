"""
Kernel transaction boundary (P0 phase 1) with expected-rejection commit
semantics.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.2 Seal Transaction Ordering Contract
- v11 §22.6 Capability Token Lifecycle Contract
- v11 §24.2 INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED
- foundation §6 (P0 sealing + crash-window proofs)

Design:

`kernel.stores.sqlite.wal_recovery.open_connection` opens the database
with `isolation_level=None` for explicit transactional control. Without
an explicit BEGIN, every DML statement runs as its own implicit
transaction. Stage admission therefore performs capability consume,
service effect, artifact insert, and audit append as independent
autocommitted writes, leaving the kernel atomicity invariant
caller-discipline-dependent. `KernelUnitOfWork` is the narrow boundary
that pulls these steps into a single success-or-rollback unit.

A blanket "ROLLBACK on any exception" boundary is incorrect for this
repository because several kernel services intentionally use an
emit-rejection-audit-then-raise pattern (e.g.
`illegal_stage_transition_rejected`,
`validation_quarantine_admission_rejected`,
`capability_token_consume_rejected`,
`approval_barrier_rejected`,
`approval_seal_time_barrier_rejected`,
`approval_barrier_evaluation_error`,
`review_self_summary_rejected`, plus governance-bound budget records).
That rejection evidence is a durable kernel decision, not an unexpected
runtime crash. AT-015 forensic reconstructability requires it to
survive the failed admission.

This UoW therefore takes a `commit_on_expected_rejection` tuple of
exception types whose appearance signals "the boundary itself behaved
correctly; the stage admission was refused on governance grounds and
the rejection evidence inside the transaction must persist". On those
exception types the UoW issues `COMMIT` and lets the exception
propagate so the caller can re-raise / fail-closed normally. On any
other exception the UoW issues `ROLLBACK`, preserving the strict
all-or-nothing posture for unexpected runtime failures.

Phase-1 scope:
- Outermost UoW issues `BEGIN IMMEDIATE` on entry, `COMMIT` on success
  and on expected-rejection, `ROLLBACK` on unexpected exception.
- Nested UoWs (entered when a parent UoW already opened a transaction)
  are no-ops; the parent owns the boundary.

Out of scope:
- Multi-connection coordination.
- Savepoints / nested rollback semantics.
- Hard guard rejecting every audit append outside a UoW (deferred).
"""

from __future__ import annotations

import sqlite3
from typing import Optional, Tuple, Type


class KernelUnitOfWork:
    """Kernel-owned SQLite transaction boundary.

    Usage:
        with KernelUnitOfWork(conn, commit_on_expected_rejection=(...)):
            # multiple DML statements run inside one transaction
            ...

    Re-entrancy:
        A nested `with KernelUnitOfWork(conn)` while the same connection
        is already in a transaction is a no-op; the outer scope owns the
        commit/rollback decision.

    Expected governance rejection:
        Pass concrete kernel rejection exception classes via
        `commit_on_expected_rejection` so that emit-then-raise rejection
        audits inside the transaction commit (durable evidence) while
        the exception still propagates. Truly unexpected exceptions
        (e.g. `RuntimeError`, `sqlite3.Error`, `KeyError`,
        `AssertionError`) trigger `ROLLBACK`.
    """

    __slots__ = ("_conn", "_opened", "_commit_on_expected_rejection")

    def __init__(
        self,
        conn: sqlite3.Connection,
        commit_on_expected_rejection: Tuple[Type[BaseException], ...] = (),
    ) -> None:
        self._conn: sqlite3.Connection = conn
        self._opened: bool = False
        self._commit_on_expected_rejection: Tuple[Type[BaseException], ...] = (
            tuple(commit_on_expected_rejection)
        )

    def __enter__(self) -> "KernelUnitOfWork":
        if not self._conn.in_transaction:
            self._conn.execute("BEGIN IMMEDIATE")
            self._opened = True
        else:
            self._opened = False
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[object],
    ) -> bool:
        if not self._opened:
            # Nested no-op: an outer UoW (or a caller-managed transaction)
            # owns the commit/rollback decision.
            return False
        if exc_type is None:
            self._conn.execute("COMMIT")
            return False
        if self._commit_on_expected_rejection and issubclass(
            exc_type, self._commit_on_expected_rejection
        ):
            # Expected governance rejection: commit the rejection
            # evidence emitted inside the transaction, then let the
            # exception propagate so the caller can fail-closed.
            self._conn.execute("COMMIT")
            return False
        # Unexpected runtime failure: roll back to avoid partial-effect
        # state, then let the exception propagate.
        self._conn.execute("ROLLBACK")
        return False
