# Rollback And Remediation Plan

## Purpose

Define how the readiness audit handles findings, failures, unsupported
claims, and workflow risks without pretending remediation already happened.

## Audit-Level Rollback

If an audit finding is unsupported:

1. downgrade the claim
2. mark the evidence `EVIDENCE_PENDING` or `rejected`
3. notify the buyer sponsor if the change affects conclusions
4. update the audit log
5. revise the readiness scorecard

## Workflow Remediation Categories

| Category | Example | Recommended Response |
| --- | --- | --- |
| Missing owner | No one owns AI-code production risk. | Assign risk owner before readiness claim. |
| Missing evidence | PR/test/review artifacts unavailable. | Define minimum evidence and capture process. |
| Weak review gate | AI-assisted changes reviewed inconsistently. | Add risk-tiered review gate. |
| Weak rollback | Failure path unclear. | Define rollback owner, trigger, and record. |
| Unsafe external claim | Team wants stronger wording than evidence supports. | Replace with bounded language and limitation. |

## Production Boundary

The entry audit may recommend rollback and remediation controls. It does not
execute production rollback, deployment, data migration, or system changes.

## Remediation Record

Record:

- finding
- risk tier
- owner
- recommended action
- evidence required
- approval required
- status
- date reviewed

## Completion Boundary

A remediation recommendation is not a completed remediation. Completed
remediation requires evidence from the buyer or a separately approved
implementation scope.
