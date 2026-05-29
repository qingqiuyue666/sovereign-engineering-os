# Release Candidate / Final Signoff V1 Runbook

## Scope

Release Candidate / Final Signoff V1 closes the #517 through #529 landing
sequence after every earlier priority is merged and post-merge validated. It
validates caller-supplied evidence, writes digest-only final signoff and system
status reports, and appends a local WAL event.

## Required Evidence

- frozen version tuple for `0.1.0-rc.529`
- frozen schema check with unknown schema rejection
- acceptance matrix covering focused tests, tracer discovery, full test
  discovery, `make ci`, `git diff --check`, and clean `git status --short`
- invariant sweep for fail-closed, local-first, deterministic replay, no silent
  repair, no hidden autonomy, no hidden network calls, no credential access, and
  no uncontrolled dependencies
- cleanup evidence for stale PR body/docs alignment, no placeholder blockers,
  and no TODO-as-implementation
- CI `canonical-health` success
- priority matrix showing #517 through #529 as merged and post-merge validated
- linked rollback/recovery, E2E acceptance, and security hardening runbooks

## Operator Procedure

1. Build the evidence payload from the latest branch state after full local
   validation and CI success.
2. Call `FileBackedReleaseCandidateFinalSignoff.close` with the evidence
   payload.
3. Treat any rejected gate result as a merge blocker.
4. Inspect `release-candidate-final-signoff/reports` for the final signoff and
   final system status reports.
5. Inspect `release-candidate-final-signoff/signoff.real-wal.jsonl` for the WAL
   binding.
6. Use the proposed tag only as a release tag proposal until an explicit later
   tagging task is approved.

## Linked Closure Evidence

- Rollback/recovery: `docs/runbooks/recovery_rollback_disaster_procedure_v1.md`
- E2E acceptance: `docs/runbooks/system_e2e_acceptance_v1.md`
- Security hardening: `docs/runbooks/security_abuse_boundary_hardening_v1.md`

## Fail-Closed Rules

Any missing, stale, failed, pending, untriaged, or contradictory evidence
rejects the signoff receipt. Rejected receipts still produce digest-only WAL
evidence, but they do not authorize release tagging or hidden follow-up work.
