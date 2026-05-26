# Minimal Controlled Execution Real WAL Coupling Readiness V1

## Decision

Status: BLOCKED_FOR_IMPLEMENTATION

This audit does not implement real WAL coupling for Minimal Controlled Execution.
The repository has useful journal foundations, but the currently available
paths do not provide a safe narrow append-only adapter that can persist the full
minimal preflight evidence chain without widening execution.

## Inspected Surfaces

- `kernel/runtime/event_journal.py`
- `kernel/runtime/sqlite_wal_execution_journal.py`
- `tests/tracer_bullet/test_event_journal.py`
- `tests/tracer_bullet/test_sqlite_wal_execution_journal_v1.py`
- `kernel/execution/minimal_controlled_execution_admission_wal_verifier.py`
- `kernel/execution/minimal_controlled_git_status_runner.py`

## Exact Blockers

1. The SQLite WAL journal imports `kernel.runtime.command_envelope_admission_router`.
   Minimal Controlled Execution must not couple to the broad runtime command
   envelope router because that would widen the execution surface beyond fixed
   command-specific runner slices.

2. The SQLite WAL journal accepts broad runtime admission reports and execution
   receipts, not the minimal controlled evidence contracts. A direct adapter
   would need a new mapping layer and fail-closed tests before any runner could
   depend on it.

3. The in-memory `EventJournal` is append-only and digest-only, but it stores
   only generic event descriptors. By itself it cannot persist the complete
   minimal evidence binding of request, decision, admission, receipt, failure,
   verifier input, verifier binding, pre-snapshot, and post-snapshot hashes.

4. The current minimal runners append only contract WAL evidence before
   execution through a callback. They do not yet have a narrow post-execution
   WAL event path that can record receipt, failure, and verifier hashes without
   risking execution-after-append inconsistencies.

5. Adding SQLite coupling in this phase would introduce local file mutation.
   That can be safe only with explicit fail-closed tests for append-before-
   execution, append failure, chain replay, and raw-output exclusion.

## Smallest Safe Implementation Path

1. Add a new module under `kernel/execution/` that imports only the minimal
   evidence contracts and one narrow journal interface. It must not import the
   command envelope router, local execution kernel, runtime router, scheduler,
   daemon, provider, browser, DCC, MCP, or CLI surfaces.

2. Define a minimal WAL adapter contract for digest-only records:
   request hash, decision hash, admission hash, receipt hash, failure hash,
   verifier input hash, verifier binding hash, pre-snapshot hash,
   post-snapshot hash, command id, task id, run id, sequence, and adapter hash.

3. Add an append-before-execution hook that must succeed before a runner calls
   `subprocess.run`. If the append fails, the runner must return a
   `WAL_APPEND_FAILED` failure bundle and must not execute.

4. Add a separate post-execution evidence append path for receipt, failure, and
   verifier hashes. The append path must be digest-only and must never persist
   raw stdout or stderr.

5. Add replay tests that reconstruct the evidence chain from WAL records and
   verify all hash bindings against the minimal controlled execution result.

6. Only after the adapter contract is proven against an in-memory append-only
   journal should SQLite persistence be considered. SQLite coupling must remain
   behind the same narrow adapter and must not import the broad runtime command
   router.

## Required Future Tests

- WAL append happens before execution.
- WAL append failure prevents execution.
- No raw stdout or stderr enters WAL records.
- WAL records bind request, decision, admission, receipt, failure, verifier,
  and snapshot hashes.
- No broad runtime runner import is present.
- No scheduler, daemon, CLI, provider, browser, DCC, MCP, or task graph surface
  is present.
- Replay can reconstruct and verify the evidence chain.

## Current Boundary Statement

This phase intentionally adds no new execution capability, no WAL write path,
no SQLite coupling, no runner mutation, and no import from the broad runtime
execution router. The safe next step is a narrow adapter contract PR with
fail-closed tests before any real WAL write is connected to Minimal Controlled
Execution runners or preflight.
