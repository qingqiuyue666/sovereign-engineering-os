# Real-World Validation Command Layer V1

## Validation Objective

Move SEIS from repository-prepared to reality-tested without faking
evidence.

Repository files can prepare the system. They cannot prove real buyer pain,
budget, urgency, delivery, ROI, adoption, external validation,
protocol/credit/clearing/rights maturity, capital allocation, or Stage 16
maturity.

## Minimum Human Actions

| Step | Exact Human Action | Evidence To Capture | Repository File | Next Codex Step After Evidence |
| --- | --- | --- | --- | --- |
| 1 | Choose one validation battlefield. | Chosen battlefield, rejected alternatives, decision reason, date, decision maker. | `validation/target-list-template.md` or `battlefield/first-wedge-selection.md` update. | Classify battlefield evidence and update `SEIS_16_STAGE_STATUS.md`. |
| 2 | Identify 10 real target people or teams. | Names or privacy-safe identifiers, roles, company/team segment, why each target fits. | `validation/target-list-template.md`. | Check buyer/risk-owner fit and update gap list. |
| 3 | Send 10 outreach messages. | Date sent, channel, message variant, recipient, response status. | `validation/outreach-tracker.md`. | Classify response evidence and identify objections. |
| 4 | Record all responses. | Accepted, rejected, no response, objection, referral, blocker, or unsafe request. | `validation/outreach-tracker.md` and `validation/buyer-objection-log.md`. | Update rejection rules, target profile, and next outreach language. |
| 5 | Hold 3 discovery conversations if possible. | Notes with buyer, pain, workflow, risk, budget, trigger, evidence access, objections, next step. | `validation/discovery-notes-template.md`. | Classify buyer/budget/trigger evidence and update status labels. |
| 6 | Record buyer, budget, trigger, and evidence access. | Decision maker, budget source, event creating urgency, what evidence the buyer will share. | `validation/discovery-notes-template.md`. | Update `reports/seis-16-stage-gap-list.md` and qualification rules. |
| 7 | Test one price range. | Stated range, reaction, objection, acceptance, counteroffer, no-decision reason. | `validation/pricing-feedback-log.md`. | Update pricing assumptions and transaction package. |
| 8 | Select one small real workflow. | Workflow name, boundaries, inputs, risk tier, acceptance criteria, exclusions. | `delivery-loops/client-intake-template.md`. | Prepare delivery loop and evidence package. |
| 9 | Attempt one bounded delivery. | Scope, approvals, audit log, evidence package, handoff, acceptance/incomplete/failure outcome. | `delivery-loops/case-study-capture-template.md`. | Convert delivery output into assets or failure rules. |
| 10 | Record outcome and failure honestly. | Accepted, incomplete, rejected, failed, unsafe, no-decision, or blocked reason. | `validation/close-loss-review.md`, `assets/case-library.md`, and `assets/failure-library.md`. | Update status labels, gap list, fix plan, service page, and next-action recommendation. |

## Evidence Files

Use these files for real-world evidence capture:

- `validation/target-list-template.md`
- `validation/outreach-tracker.md`
- `validation/discovery-notes-template.md`
- `validation/buyer-objection-log.md`
- `validation/pricing-feedback-log.md`
- `validation/close-loss-review.md`
- `delivery-loops/case-study-capture-template.md`
- `assets/case-library.md`
- `assets/failure-library.md`

These files are evidence containers. Empty templates or hypothetical
entries are not evidence.

## Evidence Quality Rules

Every evidence entry must include:

- source
- date
- actor
- claim supported
- limitation
- status
- next action

Allowed statuses for real-world evidence:

- pending
- accepted
- rejected
- incomplete
- failed
- superseded

Do not record private secrets, credentials, raw tokens, private keys,
browser cookies, payment details, or sensitive customer data in repository
files. Use privacy-safe summaries where needed.

## Next Codex Behavior After Evidence

When the user supplies real evidence, Codex should:

- classify evidence
- update status labels
- update gap list
- update pricing assumptions
- update rejection rules
- update service page
- update delivery templates
- update asset library
- produce next-action recommendation

Codex must not invent evidence.

## Upgrade Decision Rules

| Evidence Supplied | Possible Repository Update | Claim Still Forbidden Without More Evidence |
| --- | --- | --- |
| One outreach reply | Outreach status and objection log. | Market proof, paid signal, adoption. |
| One discovery conversation | Buyer/budget/trigger classification. | Paid customer, delivery, ROI. |
| One price objection | Pricing feedback and service page revision. | Revenue or buyer commitment. |
| One accepted scope | Delivery plan and evidence package. | Delivery completion or case study. |
| One completed delivery | Delivery status, case capture, failure or asset conversion. | Repeated service, SaaS readiness, protocol, credit, clearing, rights, capital. |
| Repeated validated deliveries | Productization readiness review. | Marketplace, protocol adoption, capital allocation unless separately evidenced. |

## Stop Condition

If no real targets are contacted, no discovery occurs, or evidence access is
not granted, stop claiming readiness advancement. Update the gap list and
revise the battlefield, offer, or outreach language.
