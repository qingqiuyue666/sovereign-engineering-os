# Codex Task Queue

## Queue Scope

Target:
`END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY`

This queue is the repository-state resume surface for Codex execution work. It
does not authorize production deployment, external validation, customer
contact, paid-signal claims, secret handling, or merges.

## NOW

| Item | Status | Evidence |
| --- | --- | --- |
| Build root Codex execution-system files | DONE | `CODEX_EXECUTION_SYSTEM.md`, `CODEX_CONTINUOUS_EXECUTION_PROTOCOL.md`, `CODEX_DONE_CRITERIA.md`, `CODEX_RISK_DOWNGRADE_POLICY.md` |
| Build queue and resume state | DONE | `CODEX_TASK_QUEUE.md`, `CODEX_PHASE_QUEUE.md`, `reports/checkpoints/continuous-execution-state.md` |
| Build skipped-risk register | DONE | `reports/checkpoints/skipped-risk-register.md` |
| Build validation matrix and delivery protocol | DONE | `CODEX_VALIDATION_MATRIX.md`, `CODEX_DELIVERY_PROTOCOL.md` |
| Add sample execution and recovery records | DONE | `reports/checkpoints/execution-sample-v1.md`, `reports/checkpoints/failure-recovery-sample-v1.md` |
| Add machine-checkable execution-system validation | DONE | `scripts/codex_execution_system_check_v1.py` |
| Preserve known untracked creative production spine | DONE | Not staged; recorded in checkpoint and final report |

## NEXT

| Item | Status | Evidence required |
| --- | --- | --- |
| Human review of draft PR | HUMAN_RESPONSIBILITY | PR review and explicit merge decision |
| Optional CI expansion after review | HUMAN_RESPONSIBILITY | Maintainer decision if the new check should become part of broader release gates beyond this PR |

## BLOCKED

| Item | Reason | Next action |
| --- | --- | --- |
| Production or external validation claims | No L4/L5 source evidence in this task | Human must provide source records before stronger claims |
| Merge to `main` | Explicitly outside authorization boundary | Human maintainer approval required |

## SKIPPED

| Item | Risk | Register |
| --- | --- | --- |
| Delete, move, or stage `reports/creative/production_spine_v1/` | Preserved local user work | `reports/checkpoints/skipped-risk-register.md` |
| Live deployment, outreach, paid APIs, secret handling | A6 human-responsibility actions | `reports/checkpoints/skipped-risk-register.md` |

## DONE

| Item | Evidence |
| --- | --- |
| Repository identity verified | `reports/checkpoints/continuous-execution-state.md` |
| Existing authority reused | `CODEX_EXECUTION_SYSTEM.md` |
| Internal execution protocol created | `CODEX_CONTINUOUS_EXECUTION_PROTOCOL.md` |
| Done criteria created | `CODEX_DONE_CRITERIA.md` |
| Risk downgrade policy created | `CODEX_RISK_DOWNGRADE_POLICY.md` |
| Validation matrix created | `CODEX_VALIDATION_MATRIX.md` |
| Delivery protocol created | `CODEX_DELIVERY_PROTOCOL.md` |

## EVIDENCE_REQUIRED

| Claim | Required evidence |
| --- | --- |
| Internal execution-system readiness | Local checks, diff, commit, draft PR, final report |
| CI status | GitHub Actions result on pushed PR head |
| Production readiness | Not in scope; requires deployment and operational source records |
| Customer validation or paid signal | Not in scope; requires dated external source records |

## HUMAN_RESPONSIBILITY

| Item | Reason |
| --- | --- |
| Merge PR | Mainline authority |
| Retarget PR if review boundary changes | Review boundary authority |
| Production deployment | External operational authority |
| Real-world outreach or validation | Human business authority |
| Secret, token, account, or permission handling | Credential authority |
