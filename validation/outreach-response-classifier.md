# Outreach Response Classifier

Status label: `OUTREACH_RESPONSE_CLASSIFIER_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Classify real outreach responses and define the next repository action without
inventing evidence.

## Response Classes

| Response type | Meaning | Status label | Next action | Evidence file to update | Codex may update repository state? |
| --- | --- | --- | --- | --- | --- |
| accepted discovery | Target agrees to a discovery conversation or equivalent workflow review. | `ACCEPTED_DISCOVERY` | Schedule/run discovery; capture workflow, pain, risk, budget, and evidence access. | `validation/outreach-log-template-v1.md`, then `validation/discovery-script-v1.md` notes or supplied evidence file | Yes, after human supplies the record. |
| asked for details | Target wants more scope, examples, risk boundaries, or price info. | `ASKED_FOR_DETAILS` | Send bounded details; do not overpromise. | `validation/outreach-log-template-v1.md` | Yes, after human supplies the request. |
| price concern | Target asks price or says price/budget may be a problem. | `PRICE_CONCERN` | Use pricing script and record reaction. | `validation/pricing-test-script-v1.md`, `validation/outreach-log-template-v1.md` | Yes, after human supplies the response. |
| trust/security concern | Target worries about data, account risk, accuracy, approvals, or control. | `TRUST_SECURITY_CONCERN` | Explain boundaries; classify whether safe to continue. | `validation/outreach-log-template-v1.md`, `validation/objection-handling-playbook-v1.md` | Yes, after human supplies the concern. |
| no budget | Target has pain but no budget path. | `NO_BUDGET` | Record as weak/medium signal depending on pain; ask for budget trigger if appropriate. | `validation/outreach-log-template-v1.md`, `validation/buyer-budget-trigger-scorecard.md` | Yes, after human supplies evidence. |
| wrong person | Target says they do not own the workflow or budget. | `WRONG_PERSON` | Ask for referral or close politely. | `validation/outreach-log-template-v1.md` | Yes, after human supplies response. |
| referral | Target points to another person. | `REFERRAL` | Create a new target slot if privacy-safe. | `validation/target-list-v1.md`, `validation/outreach-log-template-v1.md` | Yes, with privacy-safe data only. |
| no response | No reply after reasonable follow-up window. | `NO_RESPONSE` | Record no-response; adjust channel or copy after pattern. | `validation/outreach-log-template-v1.md` | Yes, after human supplies dates. |
| rejected | Target declines the offer. | `REJECTED` | Record reason; update close/loss if specific. | `validation/outreach-log-template-v1.md`, `validation/close-loss-review-template-v1.md` | Yes, after human supplies reason. |
| unsafe request | Target asks for secret handling, account-rule bypass, uncontrolled automation, or risky external action. | `UNSAFE_REQUEST` | Reject or rescope; do not deliver unsafe work. | `validation/outreach-log-template-v1.md`, `delivery-loops/failure-and-rollback-template-v1.md` if delivery had started | Yes, to record rejection/failure boundary. |
| spam/irrelevant | Response is unrelated or not a real target. | `SPAM_IRRELEVANT` | Ignore or close; do not count as market signal. | `validation/outreach-log-template-v1.md` | Yes, as a non-signal record. |

## Repository Update Rule

Codex may update repository files only after the human supplies real response
content or a privacy-safe summary. Codex must not infer responses from silence
unless the human provides the outreach dates and follow-up window.
