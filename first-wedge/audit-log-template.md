# Audit Log Template

## Purpose

Create a delivery trace that shows what was reviewed, what was claimed, what
was approved, and what remains incomplete.

## Log Header

| Field | Value |
| --- | --- |
| Client / project |  |
| Workflow audited |  |
| Buyer sponsor |  |
| Technical owner |  |
| Risk owner |  |
| SEIS executor |  |
| SEIS auditor |  |
| Start date |  |
| Close date |  |
| Status | draft / active / accepted / incomplete |

## Event Log

| Date | Actor | Event | Evidence Link | Risk Tier | Approval Needed | Status |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | yes / no |  |

## Claim Log

| Claim | Source | Verification | Auditor Decision | Limitation |
| --- | --- | --- | --- | --- |
|  |  |  | accepted / downgraded / rejected / pending |  |

## Approval Log

| Approval | Approver | Date | Conditions | Evidence |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Failure / Gap Log

| Failure Or Gap | Impact | Owner | Next Action | Status |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Rules

- Do not delete failed findings.
- Do not convert missing evidence into positive claims.
- Do not include secrets or private data.
- Use redacted links or summaries when needed.
