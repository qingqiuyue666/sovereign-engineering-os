# Decision: V12 Runtime Runner & Event Journal Foundation (v1)

## Status
Accepted — deterministic dry-run foundation implemented.

## Context
V12 requires a runtime execution foundation that is deterministic, side-effect free, and bounded by strict governance policies. The runner must validate inputs, reject forbidden operations, and produce reproducible receipts. The event journal must be append-only with duplicate detection and stage regression guards.

## Decision
Implement four core modules under `kernel/runtime/`:
1. `runner.py` — dry-run-only runtime runner with policy boundary enforcement
2. `event_journal.py` — append-only in-memory event journal with frozen descriptors
3. `state_machine.py` — deterministic state transition validator
4. `idempotency.py` — idempotency guard with duplicate detection

All modules share constraints: no provider calls, no network, no SQLite, no file mutation, no production autonomy.

## Consequences
- Foundation layer is fully deterministic and testable without external dependencies
- Real provider execution, network access, and production autonomy remain gated behind explicit policy changes
- Codex 5.5 will audit before production activation

## Governance
- `governance/runtime/runtime_runner_policy_v1.json`
- `governance/runtime/event_journal_policy_v1.json`
- `governance/runtime/runtime_state_transition_policy_v1.json`
- `governance/runtime/idempotency_policy_v1.json`
