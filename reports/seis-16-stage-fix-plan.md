# SEIS 16-Stage Fix Plan

## Purpose

Define the next fixes needed after the repository-executable 16-stage
strategic OS pass.

The highest-priority fixes are real-world actions. Repository-only work is
limited to recording evidence, correcting factual issues, and updating
status from evidence.

## Next Real-World Actions

| Step | Action | Evidence To Capture | Repository Update |
| --- | --- | --- | --- |
| 1 | Choose first validation battlefield. | Chosen battlefield, rejected alternatives, rationale, date, decision maker. | `validation/target-list-template.md` and `SEIS_16_STAGE_STATUS.md` |
| 2 | Select 10 targets. | Target name or privacy-safe identifier, role, company/team, segment, fit reason. | `validation/target-list-template.md` |
| 3 | Send outreach. | Date, channel, message, recipient, status. | `validation/outreach-tracker.md` |
| 4 | Run discovery. | Buyer/risk owner, pain, budget path, trigger, evidence access, blocker, next step. | `validation/discovery-notes-template.md` |
| 5 | Record evidence. | Source, date, actor, claim supported, limitation, status. | `validation/`, `delivery-loops/`, and `assets/` as applicable. |
| 6 | Test pricing. | Price range, reaction, objection, counteroffer, acceptance/rejection/no-decision reason. | `validation/pricing-feedback-log.md` and `assets/pricing-history.md` |
| 7 | Run bounded delivery. | Intake, scope, approvals, evidence package, audit log, handoff, acceptance/incomplete/failure record. | `delivery-loops/case-study-capture-template.md` |
| 8 | Convert delivery to assets. | SOPs, templates, cases, objections, pricing memory, failure rules, benchmarks, tool records. | `assets/` registries |
| 9 | Return evidence to repository. | Privacy-safe evidence packets and limitations. | `VALIDATION_REPORT.md`, `SEIS_16_STAGE_STATUS.md`, and relevant registries. |
| 10 | Update SEIS based on evidence. | Revised claims, gaps, service language, pricing, rejection rules, next action. | `reports/seis-16-stage-gap-list.md`, `reports/seis-16-stage-fix-plan.md`, `first-wedge/`, `transaction/`, and `validation/` |

## Repository Work Allowed Before Evidence

- Fix factual or consistency errors discovered during review.
- Keep validation commands passing.
- Clarify first-wedge language if review finds ambiguity.
- Keep this PR stacked on PR #571 unless intentionally retargeted.

## Repository Work Blocked Until Evidence

- New grand strategy layers.
- Full App implementation.
- SaaS implementation.
- Provider integrations.
- Secret handling.
- Protocol implementation.
- Credit implementation.
- Clearing implementation.
- Rights implementation.
- Capital allocation implementation.
- Fake case studies, testimonials, revenue, ROI, or delivery proof.

## Success Criteria For Next Pass

The next pass should only upgrade status if it receives real evidence:

- outreach records
- discovery notes
- pricing feedback
- close/loss outcomes
- accepted or rejected scope
- delivery evidence
- failure evidence
- asset conversion records

If no evidence arrives, the correct update is to keep real-world statuses
pending and revise the action plan.
