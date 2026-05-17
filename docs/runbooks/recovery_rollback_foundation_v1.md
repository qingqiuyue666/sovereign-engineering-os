# Recovery / Rollback Foundation v1

## Purpose
Bounded local-only recovery rollback foundation. Validates recovery
requests without performing any production mutation.

## Boundaries
- no missing rollback target
- no missing failure evidence
- no irreversible operation (DROP_TABLE, DELETE_WAL, PURGE_VAULT, HARD_DELETE, TRUNCATE)
- no production mutation
- no missing approval gate
- no real recovery execution in v1

## Operations
1. validate_recovery_request — structural validation
2. validate_rollback_plan — plan completeness
3. validate_failure_bundle_contract — failure evidence completeness
4. produce_recovery_rollback_receipt — full receipt production

## Scope
Contract-only. Does not perform any production mutation.
