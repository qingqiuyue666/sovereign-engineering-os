# Customer Feedback Intake V1

Status: `implemented_local_empty_ledger_allowed`

This intake system defines how real customer or reviewer feedback enters the
repository without fabricating traction.

## Feedback Form

Each record must include:

- feedback id;
- actor category;
- actor identity reference or redacted owner-approved label;
- date;
- source artifact;
- demo or pilot context;
- pain stated by actor;
- requested feature or concern;
- severity;
- claim supported;
- claim not supported;
- evidence link;
- follow-up owner;
- next action.

## Severity Classification

| Severity | Meaning | Required Action |
| --- | --- | --- |
| P0 | security, data loss, unsafe execution, or legal/compliance risk | stop, incident workflow, human review |
| P1 | pilot-blocking buyer concern | issue queue and owner response |
| P2 | material feature gap | roadmap issue |
| P3 | wording, packaging, or usability improvement | commercial material sync |

## Feedback-To-Issue Conversion

Feedback converts to `reports/control-plane/issue-pr-operating-queue-v1.json`
only when a source artifact exists. The issue must preserve claim boundaries
and must not transform interest, meeting, demo, or objection into payment,
customer validation, deployment, certification, or production evidence.

## Empty Ledger Rule

An empty external feedback ledger is valid. A fabricated ledger is forbidden.

