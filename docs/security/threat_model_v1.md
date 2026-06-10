# Threat Model V1

## Scope

SEOS is a local-first AI execution governance control plane. The threat model
covers repository evidence, CLI dry-run flows, approvals, receipts, replay,
context bundles, CI, release invariants, and operator review. External review is
required before any recognition or certification claim. This document does not
claim host isolation, credential custody, RPA, computer control, live provider
safety, or external certification.

## Assets

- task contracts and approval/rejection receipts
- execution receipts and failure bundles
- evidence traces and replay explanations
- AI context bundles and token ROI reports
- CI configuration and validation scripts
- release-candidate tag `v0.1.0-rc3`

## Threats

- AI approval bypass
- fake PASS after failed command
- receipt forgery or corrupted receipt JSON
- missing evidence or replay false success
- secret leakage and context leakage
- provider response poisoning
- malicious PR or patch
- CI bypass and GitHub Actions risk
- dependency risk
- operator misapproval
- tag mutation
- local path leakage

## Assumptions

The host operating system, local filesystem permissions, GitHub authentication,
and operator account security are outside SEOS runtime control. Evidence must be
digest-only or bounded text, and all unsafe states must fail closed.

## Validation

Validated by `python3 scripts/security_control_check_v1.py`,
`python3 scripts/secret_context_safety_check_v1.py`, and
`python3 scripts/release_invariant_check_v1.py`.
