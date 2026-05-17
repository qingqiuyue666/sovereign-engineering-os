# Runtime Runner & Event Journal (V12-05)

## Overview
The V12-05 foundation provides deterministic dry-run runtime execution with an append-only event journal, state machine, and idempotency guard.

## Components

### Runtime Runner (`kernel/runtime/runner.py`)
- Entry point: `run_dry_run(payload)` -> `RunnerReceipt`
- Requires `dry_run=true`
- Rejects provider, network, production autonomy, raw fields
- Pure, deterministic, side-effect free

### Event Journal (`kernel/runtime/event_journal.py`)
- `EventJournal` class with append-only semantics
- `JournalEvent` frozen descriptor (digest refs only)
- Detects duplicate `logical_sequence` per run
- Detects illegal stage regression
- Pure validation via `validate_event_record()`

### State Machine (`kernel/runtime/state_machine.py`)
- `validate_state_transition(payload)` -> `StateTransitionReceipt`
- 7 allowed states, 8 allowed transitions
- `quarantined -> planned` requires `recovery_allowed=true`
- Terminal `completed` cannot transition

### Idempotency (`kernel/runtime/idempotency.py`)
- `validate_idempotency(payload)` -> `IdempotencyReceipt` (pure)
- `IdempotencyGuard` class for stateful duplicate detection
- Same key + same digest = `duplicate_safe=true`
- Same key + different digest = rejected

## Local Verification
```bash
python3 -m unittest tests.tracer_bullet.test_runtime_runner -v
python3 -m unittest tests.tracer_bullet.test_event_journal -v
python3 -m unittest tests.tracer_bullet.test_runtime_state_machine -v
python3 -m unittest tests.tracer_bullet.test_idempotency -v
make test-runtime-runner-event-journal
```

## Constraints
- No provider calls
- No network access
- No SQLite
- No file mutation
- No production autonomy
- All functions deterministic and side-effect free
