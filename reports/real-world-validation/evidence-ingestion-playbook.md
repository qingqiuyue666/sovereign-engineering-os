# Evidence Ingestion Playbook

Status label: `EVIDENCE_INGESTION_PLAYBOOK_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Define how real outreach, discovery, pricing, delivery, failure, and feedback
evidence updates SEIS without converting assumptions into proof.

## Evidence Types

| Evidence type | Evidence file | Status label impact | What can be updated | What cannot be claimed yet | Next Codex action |
| --- | --- | --- | --- | --- | --- |
| outreach response | `validation/outreach-log-template-v1.md` | `OUTREACH_RESPONSE_RECORDED` | target status, copy, objection, next action | market proof, paid signal, delivery | classify response and update target/outreach files |
| discovery notes | `validation/discovery-script-v1.md` or supplied notes | `DISCOVERY_EVIDENCE_RECORDED` | pain, workflow, buyer, budget, trigger, evidence access | paid customer, ROI, delivery completion | score buyer/budget/trigger and recommend next action |
| pricing feedback | `validation/pricing-test-script-v1.md` | `PRICING_FEEDBACK_RECORDED` | price hypothesis, objection library, scope | validated pricing unless accepted/rejected by real buyer | update pricing history with limitation |
| objection | `validation/objection-handling-playbook-v1.md` | `OBJECTION_RECORDED` | outreach language, risk rules, offer scope | rejection pattern unless repeated | classify objection and update close/loss if needed |
| accepted scope | `delivery-loops/delivery-scope-template-v1.md` | `SCOPE_ACCEPTED_PENDING_DELIVERY` | delivery plan, acceptance criteria, evidence package | completed delivery, case study, ROI | prepare bounded delivery files |
| delivery evidence | `delivery-loops/acceptance-criteria-template-v1.md` | `DELIVERY_EVIDENCE_RECORDED` | delivery status, case capture, asset conversion decision | repeated delivery, SaaS readiness, certification | convert accepted artifacts into assets with limitations |
| failure record | `delivery-loops/failure-and-rollback-template-v1.md` | `FAILURE_RECORDED` | risk rules, failure library, scope exclusions | success case or proof asset | update failure rule and retry/defer decision |
| customer feedback | supplied privacy-safe feedback record | `CUSTOMER_FEEDBACK_RECORDED` | service language, SOP, acceptance criteria | testimonial unless approved; ROI unless evidenced | summarize feedback and record limitation |
| maintenance request | `delivery-loops/maintenance-offer-template-v1.md` | `MAINTENANCE_REQUEST_RECORDED` | maintenance offer, drift rules, support cadence | adoption proof unless accepted and used | update maintenance template and next review |

## Required Metadata

Every ingested evidence item must include:

- source
- date
- actor or privacy-safe identifier
- workflow
- claim supported
- limitation
- confidence
- next action

## Forbidden Ingestion

Do not ingest:

- secrets
- private keys
- browser cookies
- payment details
- raw sensitive customer data
- generated fake evidence
- testimonials without approval
- screenshots or documents that violate privacy/security rules

## Status Upgrade Rule

No real-world status may be upgraded unless the evidence directly supports the
upgrade and the limitation is recorded.

Repository-ready files can set `SEIS_REAL_WORLD_VALIDATION_READY`.

Only human-supplied external evidence can move beyond `HUMAN_ACTION_REQUIRED`.
