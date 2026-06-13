# Evidence Matrix Template

## Purpose

Tie every delivery claim to a source, owner, verification method, and
limitation.

## Matrix

| Claim | Evidence Source | Owner | Date | Verification | Status | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  | reviewed / not reviewed / contradicted | evidenced / pending / rejected |  |

## Required Evidence Types

- workflow artifact
- ticket or request
- PR or change artifact
- review evidence
- test evidence
- approval evidence
- release/use evidence
- rollback/remediation evidence
- risk-owner acceptance

## Rule

Any claim without evidence remains `EVIDENCE_PENDING` and must not be used
as readiness proof.
