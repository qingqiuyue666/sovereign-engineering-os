# Approval Runtime Integration V1

## Decision

Status: IMPLEMENTATION_READY

This branch integrates the existing approval runtime contract into the
human-invoked WAL-gated controlled preflight path. A preflight cannot proceed
through the new integration unless a persisted, unexpired, unrevoked, single-use
approval receipt exists for the same task, run, and approval scope.

## Safety Boundary

- Human approval is explicit: request and decision material must pass the
  approval runtime contract and the decision must be human-attested.
- No implicit auto-approval is issued by the preflight gate.
- Approval issuance and consumption append `APPROVAL_EVENT` records to the real
  WAL backend.
- Approval issuance persists a digest-only receipt file and a safe artifact
  summary.
- Missing, expired, revoked, reused, identity-mismatched, scope-mismatched, or
  tampered approval evidence fails closed before preflight append records are
  attempted.
- The older lower-level preflight API remains available as a primitive; the
  integrated controlled path is `run_approval_gated_minimal_controlled_wal_preflight`.

## Deferred Work

Failure bundle center integration, the full controlled execution lifecycle,
worker capability runtime, watchdog integration, and operator console display
remain later priorities.

## Forbidden Surfaces

This implementation introduces no subprocess execution, provider calls, network
access, browser control, daemon loop, credential access, arbitrary command
materialization, or background autonomy.
