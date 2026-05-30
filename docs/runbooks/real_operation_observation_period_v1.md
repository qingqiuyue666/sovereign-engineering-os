# Real Operation Observation Period V1

## Current State

The repository enters observation from this already completed state:

- LANDING_READY_NO_FURTHER_STAGE_REQUIRED
- MAIN_MERGED
- POST_MERGE_VALIDATED
- FINAL_RC_TAGGED
- DRAFT_RELEASE_CREATED

Anchors:

- main HEAD: 9a363f95b85602ffc598db463dc6181a9bbbdf3c
- release candidate tag: v0.1.0-rc3

## Observation Period Definition

REAL_OPERATION_OBSERVATION_PERIOD_V1 is a 30-day real operation observation period. Its purpose is to keep the project in real use, record hard evidence, and prevent default active development after the release candidate closure.

The default operating rule is: if no hard evidence blocker exists, do not continue development.

## Allowed Changes

Only blocker fixes are allowed by default, and each blocker fix must be justified by real operation evidence. A fix PR is allowed only when all of these conditions are true:

- The issue was found during real operation.
- The evidence is recorded in reports/observation/real_operation_observation_log_v1.md or reports/observation/real_operation_observation_log_v1.json.
- The issue blocks clean use, replay, receipts, release metadata consistency, security-boundary clarity, budget gates, operator runbook completion, or the approval boundary.
- The proposed fix is the smallest local-first change that resolves the blocker.
- The PR does not mutate tags, publish a public release, or introduce a new development stage.

Hard evidence blocker examples include:

- clean clone breakage
- CLI fatal bug
- evidence trace failure
- replay failure
- receipt corruption
- release, tag, or draft metadata inconsistency
- security boundary wording error
- token or context budget gate failure
- real use case blocker
- operator runbook cannot complete minimal use
- AI worker bypasses approval boundary

## Forbidden Changes

The observation period forbids:

- feature expansion
- no item 28+ continuation
- new runtime modules
- speculative V2/V3
- multi-agent expansion
- cloud-first dependency
- OS sandbox misrepresentation
- RPA/computer-control repositioning
- public release publishing
- tag movement or deletion
- speculative top-tier expansion

The observation period also rejects continuation reasons such as:

- "could be more advanced"
- "could be more top-tier"
- "future users may need it"
- "architecture would be more complete"
- "more modules would look better"
- "multi-agent would be impressive"
- "more tests would look stronger"
- "documentation could be grander"

## How To Record A Real Issue

1. Add an observation entry with the date, task or use case, evidence, severity, allowed action, and result.
2. Link or name the concrete evidence artifact when one exists, without committing secrets or machine-local absolute paths.
3. Classify the severity as one of: none, low, medium, high, or blocking.
4. State whether the allowed action is no action, documentation correction, test correction, or blocker fix.
5. Keep the result factual. Do not claim mock-only evidence as real observation evidence.

## Fix PR Decision

A fix PR may proceed only when the recorded issue is a hard evidence blocker. The PR must stay blocker-only, preserve the local-first and human-gated execution constraints, and include validation proving the blocker is fixed.

If the proposed change adds product features, item 28+, a runtime module, cloud-first dependencies, multi-agent behavior, speculative V2/V3 planning, OS sandbox claims, or RPA/computer-control repositioning, reject it during observation.

## Security Boundary

SEOS is a governance-level control plane, not an OS-level sandbox, container, VM, EDR, filesystem permission boundary, RPA system, computer-control system, or secret manager.

SEOS coordinates evidence, policy, approvals, and receipts. It does not replace host isolation, filesystem permissions, endpoint protection, secret storage, browser automation controls, or operating system security boundaries.

## Stop Condition

If no hard evidence blocker exists, do not continue development. Remain in real operation observation mode and keep the log current for the 30-day period.
