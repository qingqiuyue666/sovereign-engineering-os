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
- No autonomous AI patching.
- No commercial SaaS surface.
- No public GitHub Release publication.

## v0.1.0-rc3

- Release-candidate audit checkpoint. The tag is preserved and must remain
  unchanged for this readiness program.
