# Human Approval Flow

## Purpose

Specify how the future workbench routes decisions that models and operators
cannot approve on their own.

## Approval Types

| Approval | Required For |
| --- | --- |
| Scope approval | Starting delivery work. |
| Evidence access approval | Reviewing client artifacts. |
| Risk approval | Tier 3 or Tier 4 findings. |
| Claim approval | Client-facing readiness language. |
| External-use approval | Proof assets, public wording, case material. |
| Production approval | Any production-adjacent change, usually out of scope. |
| Secret approval | Any sensitive access, usually out of scope. |

## Approval Record

- approver
- date
- scope
- evidence reviewed
- conditions
- expiration or review date
- related artifact

## Boundary

Models can prepare approval packets. They cannot grant approval, infer
approval from silence, or bypass a required human gate.
