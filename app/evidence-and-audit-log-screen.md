# Evidence And Audit Log Screen

## Purpose

Specify the workbench surface for evidence, claims, approvals, and delivery
events.

## Evidence Record Fields

- source
- date
- owner
- related claim
- workflow step
- risk tier
- verification status
- limitation
- permission status

## Audit Event Fields

- timestamp
- actor
- action
- artifact
- risk tier
- approval required
- outcome
- limitation

## Views

- evidence by claim
- evidence by workflow step
- pending evidence
- rejected claims
- approvals required
- external-use candidates

## Controls

- unsupported claims default to `EVIDENCE_PENDING`
- rejected evidence stays visible
- external-use candidates require buyer/human approval
- no secrets or private raw evidence in the workbench unless separately
  approved and safely stored
