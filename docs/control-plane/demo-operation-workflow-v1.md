# Demo Operation Workflow V1

Status: `implemented_local_external_actor_pending`

Purpose: demonstrate the AI Agent Execution Control Plane to a buyer or
reviewer using local fixtures and evidence, without claiming customer
validation or production deployment.

## Setup

- Branch: current PR branch.
- Demo data: `reports/control-plane/task-fixtures-v1.json`.
- Validation: `make real-world-operation-check`.
- Evidence: `reports/control-plane/first-controlled-cycle-v1.json`.

## Demo Task

Run the low-risk fixture `ACP-TASK-001`. Show the task input, classifier output,
policy decision `ALLOW`, evidence ledger entry, check result, rollback note,
and resume point.

## Forbidden Task

Show `ACP-TASK-002`. The policy gate must return `DENY` for a destructive or
release-like action. The operator must show the failure ledger entry and explain
that denial evidence is a product feature.

## Failure/Resume Example

Show `ACP-TASK-003`. The policy gate must return `DRY_RUN_ONLY`, record a
simulated failed check, write a failure ledger entry, and preserve the resume
point.

## Buyer-Facing Summary

The demo may say:

`AI Agent Execution Control Plane with controlled local low-risk execution, evidence-backed safety gates, commercial validation package, real-world validation workflow, and commercial operation readiness.`

The demo must not say customer-validated, externally benchmark-proven,
certified, commercially deployed, paid by an enterprise customer, long-term
autonomy-proven, or production-observability-proven unless the external
evidence ledger supports the claim.

