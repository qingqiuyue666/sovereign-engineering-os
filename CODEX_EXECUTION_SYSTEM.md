# Codex Execution System V1

## Target

`END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY`

Current extension target:

`ELEVEN_CORE_DELIVERY_LAYERS_V1_READY`

This target means the repository has a durable internal execution system that
future Codex runs can resume from repository state. It does not mean
production readiness, external validation, customer validation, paid signal,
deployment completion, real-world operation, global maturity, or final platform
completion.

## Authority

This file is a navigation and assembly layer. It does not replace the existing
repository authority:

- `AGENTS.md` remains the default agent instruction entrypoint.
- `CLAUDE.md` remains Claude-compatible project memory.
- `docs/agent-protocols/` remains the detailed execution, risk, evidence, and
  failure-handling authority.
- `docs/aoos/` remains the AOOS cross-domain routing and interface layer.
- `validation/` and `reports/real-world-validation/` remain the real-world
  evidence boundary.

## Operating Rules

Codex runs must use current-state-first execution:

1. Verify repository root, remote, current branch, worktree status, and PR state
   when relevant.
2. Inspect existing protocol files, reports, scripts, tests, and CI before
   adding new structure.
3. Work continuously toward the requested terminal state instead of stopping at
   one file, one phase, one checkpoint, one commit, or one draft PR.
4. Downgrade risk before stopping globally.
5. Skip and record unsafe local actions, then continue remaining safe work.
6. Preserve evidence for material claims.
7. Resume from repository state files rather than chat memory.

## Required System Files

- `CODEX_CONTINUOUS_EXECUTION_PROTOCOL.md`
- `CODEX_DONE_CRITERIA.md`
- `CODEX_RISK_DOWNGRADE_POLICY.md`
- `CODEX_TASK_QUEUE.md`
- `CODEX_PHASE_QUEUE.md`
- `CODEX_VALIDATION_MATRIX.md`
- `CODEX_DELIVERY_PROTOCOL.md`
- `reports/checkpoints/continuous-execution-state.md`
- `reports/checkpoints/skipped-risk-register.md`
- `reports/checkpoints/execution-sample-v1.md`
- `reports/checkpoints/failure-recovery-sample-v1.md`
- `reports/checkpoints/end-to-end-execution-system-v1-final-report.md`
- `CODEX_EXTERNAL_SOURCE_INTAKE_REGISTRY.md`
- `CODEX_REAL_TASK_THROUGHPUT_LAYER.md`
- `CODEX_ACCEPTANCE_CASE_LIBRARY.md`
- `CODEX_STRONG_VALIDATION_LAYER.md`
- `CODEX_EXTERNAL_PATTERN_ABSORPTION_LAYER.md`
- `CODEX_PERMISSION_SECURITY_LAYER.md`
- `CODEX_PRODUCT_DELIVERY_LAYER.md`
- `CODEX_RUNTIME_STATE_MEMORY_LAYER.md`
- `CODEX_REVIEW_ANTI_HYPE_LAYER.md`
- `CODEX_ORGANIZATIONAL_OPERATING_LAYER.md`
- `CODEX_OPERABILITY_READINESS_LAYER.md`
- `reports/checkpoints/eleven-core-delivery-layers-v1-final-report.md`
- `reports/checkpoints/eleven-core-delivery-layers-scorecard-v1.md`

## Eleven-Layer Delivery Loop

The `ELEVEN_CORE_DELIVERY_LAYERS_V1_READY` extension wires these flows:

- external source intake -> frontier gap search
- frontier gap search -> project absorption shortlist
- project absorption shortlist -> benchmark criteria
- benchmark criteria -> acceptance cases
- acceptance cases -> validation
- real task ledger -> runtime state ledger
- permission/security policy -> delivery protocol
- product delivery layer -> validation matrix
- review/anti-hype -> final report
- organizational operating -> reviewer/security/data/release/human responsibility queues
- operability readiness -> rollback
- 100-point maturity ladder -> continuous maturity iteration queue

## Acceptance Criteria

The internal-ready target is satisfied when all of these are true:

- The repository has root-level Codex execution rules that point to existing
  authority instead of creating a competing protocol stack.
- The task and phase queues contain NOW, NEXT, BLOCKED, SKIPPED, DONE,
  EVIDENCE_REQUIRED, and HUMAN_RESPONSIBILITY states.
- The checkpoint state file lets a future run resume without chat memory.
- The skipped-risk register records unsafe actions, downgrade attempts,
  whether continuation was safe, and the next human action.
- The validation matrix defines checks for documentation, code, and app
  changes, plus how to record checks that cannot run.
- The delivery protocol defines branch, commit, PR, checks, skipped checks,
  final report, target status, and no-merge behavior.
- A real or fixture execution sample exists.
- A real or fixture failure/recovery sample exists.
- Local validation has run and any skipped checks are recorded.
- A final delivery report records status, evidence, limitations, skipped risk,
  blocked items, and remaining human-responsibility work.

## Anti-Fake-Completion Boundary

Repository artifacts can be `READY_FOR_REVIEW` or
`END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY`. They cannot by themselves
prove external validation, customer acceptance, paid signal, real delivery,
production deployment, commercial adoption, global maturity, or final platform
completion.

## Rollback

Rollback is repository-only:

- Revert the branch commit or follow up with a corrective commit.
- Do not rewrite public history unless a human explicitly authorizes it.
- Do not delete preserved local artifacts.
- Preserve final reports, skipped-risk records, and validation output.
