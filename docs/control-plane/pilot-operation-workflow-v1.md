# Pilot Operation Workflow V1

Status: `implemented_local_external_actor_pending`

This workflow prepares a safe commercial pilot. It does not start a real pilot
or contact customers automatically.

## Target User

Primary target: engineering leader, platform owner, AI tooling owner, security
reviewer, or operations owner who needs governance over agentic engineering
work.

## Pilot Task Set

| Task | Boundary | Success Metric |
| --- | --- | --- |
| low-risk repo documentation task | local repository only | allowed task produces evidence ledger and check result |
| forbidden command attempt | fixture only | denial is recorded with no side effect |
| failure/recovery sample | dry-run only | failure ledger and resume point are complete |
| commercial material sync | docs only | buyer material matches evidence and no-claim audit passes |
| external evidence intake | manual entry only | feedback record converts to issue queue without fabrication |

## Allowed Data Boundary

Use only non-secret repository artifacts, local fixtures, and customer-approved
pilot data. Do not ingest secrets, personal data, proprietary code, private
logs, payment data, or customer production systems unless a written pilot scope
and data handling approval exist.

## Review Cadence

- kickoff: confirm scope, success metrics, data boundary, support boundary, and
  no-fabrication rule;
- weekly review: evidence ledger, blocker ledger, customer feedback, issue
  queue, pricing objections, and residual risks;
- exit review: supported claims, unsupported claims, next action, and paid
  pilot gate.

## Exit Criteria

Pilot may advance only when the tracker contains real actor, date, artifact,
claim supported, claim not supported, confidence, and next action. Payment or
procurement readiness requires the paid-pilot readiness gate.

## Paid-Pilot Gate

See `docs/control-plane/paid-pilot-readiness-gate-v1.md`.

