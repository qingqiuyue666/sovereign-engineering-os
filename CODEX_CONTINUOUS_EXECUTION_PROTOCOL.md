# Codex Continuous Execution Protocol

## Purpose

Define how Codex executes repository work end to end without turning the human
into a relay, while still stopping at real human-responsibility gates.

## Terminal-State Execution

When a target state is defined, Codex should continue all safe work until one
of these terminal states is true:

- `ACHIEVED`: acceptance criteria are met and evidence exists.
- `PARTIAL`: safe work is complete, but one or more scoped items are skipped,
  blocked, or require human responsibility.
- `BLOCKED`: continuing would create fake completion or all remaining work
  requires non-automatable human responsibility.

Intermediate phases are internal verification points, not handoff points.

## Phase Chain

### Phase 0: Current State Audit

Inspect branch, remote, worktree, existing rules, README/docs, reports,
scripts, tests, CI, task queues, checkpoint files, and current repository
claims versus evidence.

Exit evidence:

- current branch and base
- preserved local artifacts
- existing authority files
- missing execution-system files
- available validation commands

### Phase 1: Execution Foundation

Create or update:

- `AGENTS.md`
- `CODEX_EXECUTION_SYSTEM.md`
- `CODEX_CONTINUOUS_EXECUTION_PROTOCOL.md`
- `CODEX_DONE_CRITERIA.md`
- `CODEX_RISK_DOWNGRADE_POLICY.md`

The files must encode current-state-first execution, no human relay,
terminal-state execution, risk downgrade, skip-and-record, evidence before
claims, final report behavior, repository-state resume, and anti-fake
completion.

### Phase 2: Task Queue And State Continuation

Create or update:

- `CODEX_TASK_QUEUE.md`
- `CODEX_PHASE_QUEUE.md`
- `reports/checkpoints/continuous-execution-state.md`
- `reports/checkpoints/skipped-risk-register.md`

The state file must let a future Codex run resume from repository evidence
without chat memory.

### Phase 3: Validation Matrix

Create or update `CODEX_VALIDATION_MATRIX.md` with validation levels for
documentation, code, app, CI, skipped checks, and check owners.

### Phase 4: Delivery Protocol

Create or update `CODEX_DELIVERY_PROTOCOL.md` with branch, commit, PR, changed
files, checks, skipped checks, skipped-risk records, final report, target
status, and no-merge rules.

### Phase 5: Execution Sample

Create or update `reports/checkpoints/execution-sample-v1.md` with a minimal
loop:

Task target -> current state -> risk classification -> safe action -> evidence
-> validation -> final status.

### Phase 6: Failure / Recovery Sample

Create or update `reports/checkpoints/failure-recovery-sample-v1.md` with a
failed or blocked action, downgrade attempt, local skip or block decision,
evidence, resume instruction, and next human action if required.

### Phase 7: Claim Reduction And Navigation Cleanup

Inspect repository language for unsupported claims. Prefer claim downgrade,
future-state labeling, archive maps, and navigation reduction over destructive
deletion.

### Phase 8: Final Validation

Run safe available checks. At minimum:

```bash
git diff --check
```

Run the narrowest relevant repository check. Record unavailable checks instead
of pretending they passed.

### Phase 9: Branch / Commit / Draft PR

Use a dedicated branch. Commit scoped work, push, and open a draft PR when
authenticated and safe. Do not merge and do not push directly to `main`.

### Phase 10: Final Report

Create or update
`reports/checkpoints/end-to-end-execution-system-v1-final-report.md` with
status, evidence, checks, skipped items, blocked items, human-responsibility
items, known limitations, and the explicit non-claim statement.

## Stop Conditions

Stop globally only when:

- repository identity does not match the requested target
- unrelated dirty changes make staging ambiguous
- a required check fails after one narrow retry
- auth is unavailable for a required publish action
- continuing would create fake completion
- all remaining work requires human responsibility

Otherwise, downgrade locally, record the risk, and keep moving.
