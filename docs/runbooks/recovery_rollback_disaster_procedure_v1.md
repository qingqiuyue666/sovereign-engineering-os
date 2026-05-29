# Recovery Rollback Disaster Procedure V1

Status: implemented for #526.

## Purpose

This runbook defines the local, receipt-backed procedure for recovering a
runtime after corruption, failed migration, partial write, or crash during
state transitions. The procedure is fail-closed: corrupted or ambiguous sources
are copied into quarantine and are never silently repaired.

## Supported Procedures

- runtime backup
- restore from snapshot
- restore from WAL plus artifact manifest
- failed migration rollback from backup
- corrupt store quarantine
- partial write recovery
- crash during write recovery
- crash during snapshot recovery
- crash during approval/queue transition recovery

## Operator Flow

1. Create a backup before any restore or rollback mutation.
2. Validate source evidence before use.
3. Restore only from a valid snapshot or a valid WAL plus artifact manifest.
4. If validation fails, quarantine the source and stop.
5. For failed migrations, restore from the prior backup and quarantine the
   failed migration marker.
6. For partial writes, preserve the stable state and quarantine the partial
   file.
7. For snapshot or approval/queue transition crashes, quarantine the crash
   marker and require manual review.
8. Verify the deterministic receipt hash before resuming runtime work.

## Receipt Guarantees

Every procedure emits a `recovery_rollback_disaster_procedure_v1` receipt with:

- procedure name
- accepted/rejected status
- failure codes
- backup hash when a backup is used
- source and target paths
- quarantine paths
- restored state hash when a state is restored or preserved
- deterministic verification hash
- next operator action

Receipts declare:

- `no_silent_repair = true`
- `repair_performed = false`
- `network_accessed = false`
- `subprocess_spawned = false`
- `sensitive_material_read = false`

## Fail-Closed Cases

The procedure rejects and quarantines:

- snapshot JSON parse failure
- snapshot state hash mismatch
- WAL JSON parse failure
- WAL sequence gaps
- WAL previous-hash mismatch
- WAL event-hash mismatch
- missing or mismatched artifact manifest entries
- crash marker during snapshot recovery
- ambiguous approval/queue transition marker
- non-failed migration marker

## Quarantine Rule

Quarantine copies are written under `quarantine/<reason>/...`. The original
source remains in place for operator review. The procedure does not delete or
rewrite corrupted source evidence.

## Validation

Focused:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_recovery_rollback_disaster_procedure_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_recovery_rollback_disaster_procedure_v1 -v
```

Full gates:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
make ci
git diff --check
git status --short
```
