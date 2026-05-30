# Real-World Operation Evidence Program V1

Status: REAL_WORLD_OPERATION_EVIDENCE_PROGRAM_INITIALIZED

This program defines the evidence required before any future final recognition
analysis can rely on real-world operation. It does not claim elapsed-time
operation evidence has already been collected.

External recognition is not confirmed by Codex.
Global top engineer signoff is not confirmed by Codex.
Human or independent external review remains required.
30-90 day real-world operation evidence remains required.
No elapsed-time evidence is fabricated.

## Observation Windows

- 30-day minimum observation window: required before the first operation
  evidence completion review.
- 90-day stronger observation window: preferred before stronger external
  review or final recognition analysis.
- Current day count at initialization: 0.

## Minimum Future Evidence Requirements

- At least 10 real SEOS-governed tasks.
- At least 5 real PRs governed by SEOS.
- At least 3 real failure or exception cases.
- At least 1 rollback/recovery drill.
- At least 1 dependency/update or release drill.
- Repeated verification checks over time.

## Task Evidence Schema

Each task record must include task id, objective digest or bounded summary,
operator intent, approval boundary, execution mode, evidence artifacts,
validation commands, result, residual risk, and linked PR or commit evidence
where applicable.

## PR Evidence Schema

Each PR record must include PR URL, title, branch, merge commit, merge time,
validation commands, GitHub check status, boundary statement, and post-merge
validation evidence.

## Failure Evidence Schema

Each failure or exception record must include failure id, trigger, observed
behavior, failed command or procedure, severity, containment action, replay or
diagnostic evidence, remediation, validation, and residual risk.

## Incident Evidence Schema

Each incident record must include incident id, severity, impact, timeline,
triage notes, containment, evidence preservation, rollback or recovery action,
communication boundary, and closure criteria.

## Rollback/Recovery Drill Schema

Each rollback or recovery drill must include drill id, trigger, rollback plan,
safe rollback procedure, evidence preserved, validation command, result, and
lessons recorded. Force-pushing protected history is not an accepted rollback
method.

## Dependency/Update Drill Schema

Each dependency, update, or release drill must include change id, dependency or
release surface, risk review, validation plan, commands run, result, rollback
path, and follow-up decision.

## Validation Command Schema

Each validation record must include command, working tree state, required flag,
exit code, result, artifact reference, and whether the command was local,
GitHub-hosted, or both.

## Daily/Weekly Rollup Schema

Daily rollups must include date, day index, tasks completed, PRs merged,
failures observed, incidents observed, validations run, unresolved risks, and
next-day follow-up. Weekly rollups must summarize trends, repeated failures,
validation stability, open risks, and whether the observation window remains
credible.

## Stop Conditions

Stop collection and require human review if tag integrity is affected, protected
history would need rewriting, secrets are needed, live provider credentials are
required, uncontrolled runtime capability is proposed, audit gates would need to
be weakened, or evidence would need to be fabricated.

## Escalation Conditions

Escalate to a human reviewer if P0/P1 findings appear, GitHub-hosted checks fail
without a safe minimal fix, external review contradicts repository evidence, a
security control boundary is unclear, or operational evidence cannot be
collected without forbidden capability.

## Final Operation Evidence Report Requirements

A future final operation evidence report must include the actual observation
window start and end, elapsed days, all task and PR records, failure and incident
records, rollback/recovery and dependency/update drills, repeated verification
history, unresolved risks, external review status, and explicit non-claims for
any evidence still missing.

## Day 000 Initialization

The Day 000 initialization record is:

- `reports/operations/operation_day_000_initialization_v1.json`
- `reports/operations/operation_day_000_initialization_v1.md`

It records the current main head, rc3 tag state, and the real PR evidence from
this Codex run. It does not satisfy the 30-day or 90-day observation windows.
