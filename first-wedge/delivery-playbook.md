# Delivery Playbook

## Purpose

Turn the AI Production Governance Readiness Audit into a repeatable delivery
process that produces evidence, not just output.

## Delivery Status

Repository status: `EXECUTION_KIT_READY`.

Real-world status: `REAL_DELIVERY_PENDING`.

## Roles

| Role | Responsibility | Boundary |
| --- | --- | --- |
| Buyer sponsor | Approves scope, budget, acceptance, and use of proof assets. | Cannot be replaced by model output. |
| Technical owner | Explains workflow and validates technical facts. | Does not approve external claims alone. |
| Risk owner | Owns readiness risk and remediation priority. | Must approve high-risk findings language. |
| SEIS executor | Conducts review and prepares artifacts. | Cannot self-certify high-risk findings. |
| SEIS auditor | Reviews claims, evidence, gaps, and handoff package. | Must be separated from executor when risk is material. |

## Delivery Flow

1. Intake and qualification.
2. Scope confirmation.
3. Evidence request and access approval.
4. Current-state workflow map.
5. Risk tiering.
6. Review-gate and approval mapping.
7. Evidence matrix construction.
8. Findings and recommendations.
9. Auditor review.
10. Buyer handoff and acceptance.
11. Post-delivery review and asset capture.

## AI Output Rule

AI, Codex, Claude, GPT, local models, and worker tools may draft, organize,
summarize, compare, or propose. Their outputs are claims until verified by
evidence and accepted by the relevant human owner.

## Material Risk Rule

Executor and auditor must be separated when findings could affect external
claims, production readiness, customer/security review, budget approval,
legal/compliance posture, or high-risk engineering decisions.

## Required Evidence

Every delivery must produce:

- scope record
- evidence matrix
- risk-tier map
- review-gate map
- human approval record
- audit log
- failure or limitation record
- handoff package
- post-delivery review

## No Production Authority

This playbook does not authorize production changes, deployment, credential
handling, live provider setup, or external publication. Those actions require
separate explicit approval and risk controls.
