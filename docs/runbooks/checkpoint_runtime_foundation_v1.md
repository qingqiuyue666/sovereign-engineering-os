# Checkpoint Runtime Foundation v1

## Purpose
Bounded local-only checkpoint runtime foundation. Validates checkpoint
requests without creating real checkpoints.

## Boundaries
- no checkpoint without hash
- no checkpoint without source revision
- no checkpoint without rollback reference
- no checkpoint on dirty unapproved state
- no production mutation
- no real checkpoint mutation in v1

## Operations
1. validate_checkpoint_request — structural validation
2. validate_checkpoint_scope — scope completeness
3. validate_checkpoint_integrity_contract — hash integrity
4. produce_checkpoint_runtime_receipt — full receipt production

## Scope
Contract-only. Does not create real checkpoints.
