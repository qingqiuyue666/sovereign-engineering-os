# Human Approval Points

## Purpose

Name the moments where human approval is mandatory for the readiness audit.

## Mandatory Approval Points

| Point | Approver | Required Before |
| --- | --- | --- |
| Scope approval | Buyer sponsor | Any delivery work beyond discovery. |
| Evidence access approval | Evidence owner or technical owner | Reviewing client artifacts. |
| Risk-tier approval | Risk owner | Finalizing high or material risk findings. |
| Claim-language approval | Risk owner and SEIS auditor | Client-facing readiness statements. |
| External-use approval | Buyer sponsor | Case notes, proof assets, posts, service-page claims, or references. |
| Scope expansion approval | Buyer sponsor | Adding workflows, implementation support, production-adjacent work, or new price/timeline. |
| Closeout approval | Buyer sponsor | Marking delivery accepted. |

## Always Requires Human Approval

- high-risk claims
- external claims
- secret or credential exposure decisions
- production changes
- live provider admission
- customer/security/audit response wording
- final readiness, acceptance, or completion claims

## AI Boundary

AI systems may draft approval requests and summarize evidence. They cannot
grant approval, infer approval from silence, or turn an unapproved claim into
accepted delivery.

## Approval Record

Each approval record must include:

- approver
- date
- scope approved
- evidence reviewed
- limitations accepted
- conditions or exceptions

If approval is missing, the related item remains `HUMAN_ACTION_REQUIRED`.
