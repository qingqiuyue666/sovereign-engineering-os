# Real Replay Engine Runtime v1

## Purpose
Bounded local-only replay engine runtime. Validates replay requests, binds
evidence, produces deterministic receipts, and captures failures. Does not
perform actual replay execution in v1.

## Boundaries
- no cloud re-query
- no nondeterministic replay
- no network calls
- no subprocess execution
- no cloud AI API calls
- no live provider execution
- no trading
- no production deployment
- no evidence mutation
- no raw payload in receipts
- no wall-clock time in hash or receipt generation
- no secret material reads

## Architecture

### ReplayAnchor
Immutable anchor binding replay request to input snapshot, version tuple,
and environment fingerprint. Rejects cloud re-query and nondeterministic modes.

### ReplaySnapshot
Immutable input snapshot binding identified by content hash.

### ReplayVersionTuple
Validates policy, code, and environment versions. All three must be present.

### ReplayMismatch / MismatchReport
Captures and reports replay output mismatches. Produces deterministic
mismatch reports with hashed content. Never includes raw payload.

### ReplayReceipt / ReplayReadinessReceipt / ReplayFailureReceipt
Deterministic receipts for replay operations. Readiness receipt produced
before any replay attempt. Failure receipt for corrupted evidence or
invalid requests.

### ReplayEvidenceBinding
Binds replay requests to evidence vault records. Rejects corrupted evidence
(fail-closed).

### ReplayModes
Validates replay mode. Allowed: strict, dry_run. Forbidden: cloud_requery,
nondeterministic, live, production, network, external, remote.

### ReplaySecurity
Security boundary enforcement: no network, no secrets, no raw payload in
receipts, deterministic only, fail-closed.

### ReplayCanonicalHash
Deterministic hash generation using blake2b, sha256, or sha512. No wall-clock
time. No random nonce. No raw payload in hash inputs.

### ReplayFailures / ReplayFailure
Structured failure capture. Evidence corruption triggers fail-closed behavior.

## Operations
1. create_anchor — immutable replay anchor
2. bind_snapshot — input snapshot binding
3. validate_version_tuple — version validation
4. bind_evidence — evidence vault binding
5. check_readiness — pre-replay readiness gate
6. produce_receipt — deterministic replay receipt
7. produce_failure_receipt — failure receipt
8. record_failure — structured failure capture
9. add_mismatch — mismatch reporting

## Receipt Types
- ReplayReceipt: standard replay receipt (anchor, snapshot, version tuple, status, mode)
- ReplayReadinessReceipt: readiness gate receipt with all gates
- ReplayFailureReceipt: failure receipt with code and reason

## Scope
Contract-only in v1. Does not perform actual replay execution. All receipts
are deterministic given the same inputs.
