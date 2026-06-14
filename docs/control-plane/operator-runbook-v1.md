# AI Agent Control Plane Operator Runbook V1

Status: `implemented_local`

This runbook tells an operator how to run the local readiness package without
claiming external validation.

## Preflight

1. Confirm repo root, remote, branch, worktree, PR state, and preserved local
   residue.
2. Review `docs/control-plane/full-stack-operation-registry-v1.md`.
3. Run `make controlled-execution-check`.
4. Run `make commercial-readiness-check`.
5. Run `make real-world-validation-check`.
6. Run `make real-world-operation-check`.

## Operating Sequence

| Step | Action | Evidence |
| --- | --- | --- |
| intake | Load a task from `reports/control-plane/task-fixtures-v1.json` or a matching external request | task input record |
| classify | Apply task and risk classifier | classifier output |
| gate | Emit ALLOW, DRY_RUN_ONLY, REQUIRE_HUMAN, or DENY | policy decision |
| execute or simulate | Run only local allowed commands or dry-run records | evidence ledger |
| recover | Record failed gates, repair attempt, blocker, and resume point | failure ledger |
| queue | Append next health, benchmark, security, feedback, and commercial sync work | recurring queue |
| audit | Run non-claim audit before any report or buyer material update | non-claim audit |

## Support Boundary

Current support boundary is local repository operation and reviewable demo/pilot
preparation. It does not include production hosting, customer data custody,
external benchmark operation, paid-pilot execution, auditor certification,
long-running telemetry, or enterprise SLA.

## Audit Export

Use `docs/control-plane/audit-log-export-v1.md` and
`reports/control-plane/evidence-ledger-v1.jsonl` to prepare a buyer or reviewer
packet. Do not export secrets, raw customer data, or private local machine
paths.

## Stop Conditions

Stop and require human approval before merge, release, tag, deployment,
external outreach, real customer contact, payment, production trial, external
benchmark run, security certification claim, secret handling, or destructive
operation.

