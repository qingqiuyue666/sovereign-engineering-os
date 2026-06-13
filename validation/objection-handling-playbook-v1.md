# Objection Handling Playbook V1

Status label: `OBJECTION_HANDLING_PLAYBOOK_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Respond to common objections while preserving evidence boundaries and safety
rules.

## Objection Table

| Objection | Meaning | Response direction | Record |
| --- | --- | --- | --- |
| too expensive | Price, scope, or urgency mismatch. | Reduce scope before reducing price; ask what outcome would justify spend. | price range, scope concern, budget owner |
| can do it myself | Buyer sees low complexity or no trust gap. | Ask what blocks them from doing it now and whether SOP/failure handling is valuable. | pain, time cost, do-it-yourself blocker |
| worried about data | Data sensitivity or privacy concern. | Offer redaction, local review, summaries, and no secret handling. | data category, allowed artifacts, exclusions |
| worried about account risk | Platform or account-control concern. | Keep actions human-approved; reject bypass or uncontrolled automation. | platform risk, manual checkpoints |
| worried AI will make mistakes | Accuracy and review concern. | Position AI output as draft until reviewed; add acceptance criteria and failure log. | error examples, reviewer |
| no time | Workflow may be painful but not urgent enough. | Offer short diagnostic or defer; ask for trigger date. | trigger, next review date |
| no budget | Pain exists but no spending path. | Ask who owns budget and what event creates budget. | budget owner, source, blocker |
| not urgent | Weak trigger. | Record no-decision and ask what would change urgency. | trigger missing |
| need boss approval | User is not economic buyer. | Provide concise scope for approver; request approval path. | approver, decision date |
| wants full automation without approval | Unsafe expectation. | Reject or rescope to human-confirmed workflow. | unsafe request, boundary |
| wants guarantee/ROI/certification | Overclaim pressure. | State that ROI/certification cannot be guaranteed; evidence is collected during delivery. | forbidden claim pressure |

## Response Principles

- Do not overpromise to overcome objections.
- Treat objections as evidence.
- If objection reveals unsafe expectations, reject or rescope.
- If budget is weak, reduce scope before discounting.
- If evidence access is blocked, do not attempt delivery.

## Repository Update Rule

After real objections are supplied, update:

- `validation/outreach-log-template-v1.md`
- `validation/pricing-test-script-v1.md` records
- `assets/objection-library.md` only if the objection is real and reusable
- `validation/close-loss-review-template-v1.md` if the opportunity closes
