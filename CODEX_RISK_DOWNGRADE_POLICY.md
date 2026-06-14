# Codex Risk Downgrade Policy

## Principle

Risk is not a default global stop signal. Downgrade the risky local action
first, record the downgrade, then continue remaining safe work.

## Risk Classes

| Class | Examples | Default action |
| --- | --- | --- |
| A0 | Read-only inspection, status checks, local docs review | Execute |
| A1 | Documentation, queue, checkpoint, and report edits | Execute with checks |
| A2 | Narrow scripts or tests that do not touch secrets or live services | Execute with focused validation |
| A3 | Branch, commit, push, draft PR | Execute only when requested and worktree scope is clear |
| A4 | Dependency, CI, or workflow changes | Keep narrow, validate locally, record residual risk |
| A5 | External-action proposal packets, permission specs, deployment plans | Draft only, no live action |
| A6 | Merge, direct main push, deployment, outreach, secret handling, paid/live API action | Human responsibility |

## Downgrade Ladder

- Delete -> archive or leave untouched.
- Merge -> draft PR.
- Direct main push -> feature branch.
- Deploy -> deployment plan.
- Live API -> local fixture.
- Secret access -> requirement spec without secret material.
- Real outreach -> message draft or validation plan.
- Permission change -> proposal.
- Large irreversible change -> small reversible PR.
- Runtime action -> dry-run or fixture.

## Skip-And-Record Rule

If a local risky action cannot be downgraded safely:

1. Skip only that action.
2. Record it in `reports/checkpoints/skipped-risk-register.md`.
3. Include risk type, reason, downgrade attempted, whether continuing was safe,
   and next human action.
4. Continue all remaining safe work.

## Global Stop Rule

Stop globally only when continuing would create fake completion or when every
remaining item requires non-automatable human responsibility.
