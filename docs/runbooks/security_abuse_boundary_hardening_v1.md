# Security / Abuse Boundary Hardening V1 Runbook

## Scope

Security / Abuse Boundary Hardening V1 validates proposed runtime authority
before execution or mutation. It records digest-only receipts and WAL events
for safe requests and rejected abuse attempts.

## Required Controls

- unsafe subprocess
- hidden network
- credential access
- path traversal
- symlink escape
- arbitrary write
- daemon default
- model/tool direct mutation
- approval/replay bypass
- mutable audit
- silent repair
- uncontrolled provider
- leakage
- environment credential capture
- console mutation bypass

## Operator Procedure

1. Submit only digest-bound authority metadata to
   `FileBackedSecurityAbuseBoundaryHardening.evaluate`.
2. Confirm the returned receipt is accepted before any downstream runtime
   boundary is allowed to continue.
3. If the receipt is rejected, treat the listed control failures as blockers.
4. Inspect `security-abuse-boundary/receipts` and
   `security-abuse-boundary/security.real-wal.jsonl` for digest-only evidence.

## Fail-Closed Rules

Any single control failure rejects the full boundary receipt. Rejected receipts
still write digest-only evidence, but they do not preserve raw payload material,
secrets, commands, URLs, provider responses, or environment values.
