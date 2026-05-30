# Observation Period Change Policy V1

## Default Reject

During REAL_OPERATION_OBSERVATION_PERIOD_V1, new development is rejected by default. The project is in a 30-day real operation observation period, not a feature phase, productization phase, runtime expansion phase, or speculative planning phase.

## Blocker-Only Exception Policy

A change may proceed during observation only as a blocker-only exception. The exception requires hard evidence from real operation, a recorded observation entry, and a smallest viable fix. If a smaller documentation, configuration, test, or validation correction resolves the blocker, do not choose a broader implementation.

New runtime modules are not allowed during observation unless a real blocker proves necessity and no smaller fix exists.

## Hard Evidence Requirement

Real operation evidence must identify an actual blocker, such as clean clone breakage, CLI fatal bug, evidence trace failure, replay failure, receipt corruption, release or tag metadata inconsistency, security boundary wording error, token or context budget gate failure, real use case blocker, operator runbook failure, or AI worker approval-boundary bypass.

Mock-only claims, hypothetical users, aesthetics, and architectural preference are not hard evidence.

## No Speculative Expansion

Reject changes justified by:

- "could be more advanced"
- "could be more top-tier"
- "future users may need it"
- "architecture would be more complete"
- "more modules would look better"
- "multi-agent would be impressive"
- "more tests would look stronger"
- "documentation could be grander"

## Explicit Prohibitions

Observation mode prohibits:

- no item 28+ continuation
- no tag mutation
- no public release publishing
- no host-isolation misrepresentation
- no cloud-first shift
- no multi-agent expansion
- no speculative V2/V3 stage
- no product feature expansion
- no RPA or computer-control repositioning

The local-first constraint remains in force. Observation fixes must preserve deterministic local validation and must not introduce cloud-first dependencies.

The human-gated execution constraint remains in force. SEOS may coordinate approvals and evidence, but it must not bypass human approval boundaries or become an uncontrolled execution framework.

## Security Boundary

SEOS is a governance-level control plane, not an OS-level sandbox, container, VM, EDR, filesystem permission boundary, RPA system, computer-control system, or secret manager.

SEOS must not be represented as host isolation, endpoint protection, a filesystem permission boundary, browser/computer control, robotic process automation, or a secret-management system.

## Tag And Release Boundary

Do not mutate, move, or delete existing tags during observation. Do not publish the draft release publicly during observation unless a separate owner decision explicitly authorizes release publication outside this policy.

## Stop Rule

If no hard evidence blocker is recorded, no further development stage is required. Continue only real operation observation.
