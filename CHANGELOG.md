# Changelog

All notable public-readiness changes are tracked here. This file does not claim
external recognition or final signoff.

## Unreleased

### Added

- Public identity documentation for SEOS current state and boundaries.
- Non-goals documentation covering OS sandboxing, RPA, computer control,
  autonomous AI execution, secret custody, and commercial SaaS claims.
- Local-first quickstart for install, CLI invocation, validation, evidence, and
  replay flows.
- Control-plane architecture document for task, approval, receipt, evidence,
  replay, failure, and release-check objects.
- `scripts/identity_boundary_check_v1.py` and matching tracer-bullet tests.
- Reproducibility and installability smoke scripts for clean clone, fresh venv,
  and packaging entrypoint checks.
- `scripts/installability_check_v1.py` and matching tracer-bullet tests.
- V1 contract documents for core task, approval, rejection, execution,
  evidence, replay, failure, observation, AI context, token ROI, provider,
  release-check, and audit-packet objects.
- Claim-to-evidence matrix artifacts for bounded public claims and external
  review handoff.
- `scripts/contract_check_v1.py`, `scripts/claim_to_evidence_check_v1.py`, and
  matching tracer-bullet tests.
- Fail-closed and adversarial smoke coverage for missing tasks, bad workspaces,
  duplicate task ids, rejected tasks, corrupted evidence, tag mismatch, fake
  PASS logs, path traversal, shell metacharacters, Unicode/long fields, and
  prompt-injection text.
- `scripts/failure_path_smoke_v1.sh`, `scripts/adversarial_smoke_v1.py`, and
  failure-path baseline reports.
- Security and supply-chain evidence docs covering threat model, abuse cases,
  security controls, secret/context safety, operator review, dependency policy,
  GitHub Actions policy, provenance/checksum policy, and SBOM strategy.
- `scripts/security_control_check_v1.py`, `scripts/supply_chain_check_v1.py`,
  `scripts/secret_context_safety_check_v1.py`, `scripts/release_invariant_check_v1.py`,
  and matching tracer-bullet tests.
- AI-provider admission safety docs covering provider admission,
  proposal-first flow, secret references, context redaction, token budgets,
  model output artifacts, human approval before patch, and provider failure
  handling.
- `scripts/ai_admission_check_v1.py` and matching tracer-bullet tests.
- Dogfooding evidence index and records for real merged repository-maintenance
  tasks covering identity/docs, installability, fail-closed behavior, AI
  admission safety, and security/supply-chain hardening.
- `scripts/dogfood_evidence_check_v1.py` and matching tracer-bullet tests.
- Reliability baseline report covering repeated smoke, multi-task,
  multi-workspace, approval/reject/run, evidence/replay, failure-path, elapsed
  time, and flake-rate checks.
- Operational runbooks for incident response, rollback, maintenance,
  workspace cleanup, and interrupted runs.
- Schema versioning compatibility policy for contract and frozen schema
  changes.
- `scripts/reliability_benchmark_v1.py`,
  `scripts/schema_compatibility_check_v1.py`, and matching tracer-bullet tests.

### Changed

- Replaced stale README posture with the current
  `REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE` status.
- Expanded `SECURITY.md` with secret-safety, provider-boundary, and
  validation guidance.
- Updated examples documentation to describe current governed local examples.

### Not Added

- No OS-level sandboxing.
- No RPA or computer-control capability.
- No live AI provider execution.
- No direct AI execution or AI-applied patching.
- No autonomous AI patching.
- No commercial SaaS surface.
- No public GitHub Release publication.
- No change to the immutable `v0.1.0-rc3` tag.

## v0.1.0-rc3

- Release-candidate audit checkpoint. The tag is preserved and must remain
  unchanged for this readiness program.
