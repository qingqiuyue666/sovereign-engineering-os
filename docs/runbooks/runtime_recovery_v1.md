# Runtime Recovery v1

## Purpose
Bounded local-only recovery and failure bundle integration. Creates failure
bundles from runtime failure evidence, generates non-destructive recovery
plans, and produces deterministic recovery receipts.

## Boundaries
- no destructive recovery
- no production mutation
- no network calls
- no secret material
- no env reads
- rollback compatible only
- contract-only in v1

## Architecture

### FailureBundle
Immutable failure bundle binding failed module, failure codes, and evidence
IDs. Rejects empty evidence or missing module.

### RecoveryPlan
Immutable recovery plan from failure bundle. All steps must be
non-destructive. Rollback compatible. Rejects destructive actions.

### RecoveryReceipt
Deterministic recovery receipt. Rollback compatible. No recovery execution
in v1.

### RuntimeRecoveryCanonicalHash
Deterministic hash generation.

## Operations
1. Create failure bundle from failed module + evidence
2. Create recovery plan from bundle (non-destructive)
3. Produce deterministic recovery receipt

## Scope
Contract-only in v1. Does not execute recovery. All receipts deterministic.
