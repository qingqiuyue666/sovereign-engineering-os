# Risk Tiering

## Purpose

Classify AI-assisted engineering work so low-risk evidence gathering does
not get treated like production readiness or external claims.

## Risk Tiers

| Tier | Definition | Examples | Required Control |
| --- | --- | --- | --- |
| Tier 0 - Administrative | No production, customer, security, credential, or decision impact. | Formatting notes, internal summaries, index updates. | Basic review and source trace. |
| Tier 1 - Low Engineering | Supports engineering but does not change production behavior. | Draft tests, docs, local scripts, non-release notes. | Technical owner review. |
| Tier 2 - Workflow Relevant | Affects review, release, evidence, or operational workflow. | PR templates, review gates, test policy, release checklist. | Risk owner approval and audit log. |
| Tier 3 - Production Adjacent | Could influence production readiness or external confidence. | Readiness claims, rollback plan, customer/security review answer. | Executor/auditor separation and buyer approval. |
| Tier 4 - High Risk / External | Could create customer, legal, compliance, security, credential, or deployment exposure. | Certification language, production changes, secrets, live provider setup. | Explicit human approval; usually out of scope for entry audit. |

## Tiering Questions

- Could this affect production behavior?
- Could this affect a customer, auditor, board, investor, or regulator claim?
- Could this expose secrets, private data, or privileged systems?
- Could this change budget, acceptance, risk ownership, or release behavior?
- Would a wrong answer create material harm?

## AI Output Boundary

AI-generated tiering is only a proposal. The risk owner or auditor must
approve material Tier 2-4 classifications.

## Rejection Rule

If a prospect requires Tier 4 work inside the entry audit, reject or rescope.
The entry audit can identify Tier 4 gaps but does not execute Tier 4 actions.
