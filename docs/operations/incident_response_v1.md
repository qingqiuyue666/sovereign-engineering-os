# Incident Response V1

External review required: yes.

This runbook defines response steps for repository-local SEOS readiness
evidence and validation failures.

## Severity

- S1: Evidence integrity failure, root manifest mismatch, release tag mismatch,
  or secret/context safety failure.
- S2: CI validation failure, reliability benchmark regression, schema
  compatibility failure, or failed post-merge validation.
- S3: Documentation drift, missing evidence reference, or stale operational
  note without evidence integrity impact.

## Triage

1. Stop the affected wave and capture the failing command, branch, commit, and
   PR number.
2. Preserve the failing report, CI log link, and local command output summary.
3. Classify the issue as evidence integrity, validation logic, documentation
   drift, or operational interruption.
4. Do not invent missing evidence or mark a failed command as passed.

## Containment

Containment keeps evidence stable while the issue is understood. Do not move
or recreate release-candidate tags. Do not force push. Do not publish a public
release to mask a readiness gap.

## Evidence Preservation

Keep failing artifacts available in the PR, CI run, or local report path. If a
temporary workspace was involved, record the workspace id and command summary,
not local machine paths or secret material.

## Rollback

Use `docs/operations/rollback_runbook_v1.md` for rollback. Rollback work must
use a new commit or PR and must run the validation gate again.

## Post-Incident Review

Record the root cause, affected evidence refs, corrective PR, and residual
risk. A post-incident review must state whether independent review is still
required.
