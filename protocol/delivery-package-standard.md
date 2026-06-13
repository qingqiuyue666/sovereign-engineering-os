# Delivery Package Standard

## Purpose

Define the future standard package for SEIS delivery evidence.

## Scope

Placeholder standard for readiness audits, workflow transformations, content
supply chains, and private/local AI systems.

## Non-goals

- This is not an adopted external standard.
- This does not certify delivery quality.
- This does not require new runtime code.

## Draft Fields

| Field | Description |
| --- | --- |
| buyer_context | Anonymized buyer, industry, trigger, risk owner |
| scope | Included and excluded work |
| risk_tier | Delivery and operation risk |
| evidence_manifest | Artifacts, hashes, screenshots, reports, tests |
| acceptance_criteria | Criteria agreed before delivery |
| review_record | Executor/reviewer separation |
| rollback_or_remediation | Reversal or next-fix plan |
| proof_asset | Public/private proof output |
| asset_updates | Registry entries created |
| limitations | What was not proven |

## Operating Rules

- No package is complete without limitations.
- Acceptance criteria must be set before final delivery.
- Proof assets must preserve privacy and rights.

## Failure Modes

- Package becomes ceremonial.
- Evidence manifest omits negative findings.
- Buyer acceptance is assumed rather than recorded.

## Upgrade Path

Convert this draft into a schema after repeated packages stabilize.
