# Client Workspace Model

## Purpose

Define the record model for a future internal client workspace.

## Workspace Objects

| Object | Fields |
| --- | --- |
| Client | name, segment, buyer sponsor, technical owner, risk owner, confidentiality limits. |
| Opportunity | trigger, budget source, trust gap, price, status, next step. |
| Delivery Loop | scope, workflow, risk tier, status, acceptance, handoff. |
| Evidence Item | source, date, owner, claim, verification, limitation, permission. |
| Claim | wording, risk tier, evidence links, auditor status, approval status. |
| Approval | approver, date, scope, condition, artifact link. |
| Asset Decision | create/update/reject/defer, registry target, evidence source. |

## Status Values

- `hypothesis`
- `discovery`
- `qualified`
- `active_delivery`
- `handoff_pending`
- `accepted`
- `incomplete`
- `rejected`
- `archived`

## Permission Boundary

Client workspace records may reference evidence locations and redacted
summaries. The workbench must not become a secret store.
