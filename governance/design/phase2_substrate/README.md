# Phase-2 Substrate Re-Architecture — Design Package

Status: **design-only**. No runtime code is introduced by this package.

## Baseline (unchanged)

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
- `governance/implementation/v11_narrow_path_implementation_foundation.md`

This package neither restarts architecture nor broadens scope. It documents
*candidate* substrate choices for Phase 2 / Phase 3 internalization
(constitution §27 substrate strategy, §28 hardening loop, §30.3–§30.4
roadmap) without taking implementation actions.

## What this package answers

1. Future execution substrate on Darwin (Apple `Virtualization.framework`,
   Wasmtime / WASI, Linux/KVM sidecar / remote worker) — what each would
   own and why. → `01_execution_substrate_choices.md`
2. Modules that must remain Python control-plane.
   → `02_python_control_plane_modules.md`
3. First candidates for Rust downshift.
   → `03_rust_downshift_candidates.md`
4. Future replay substrate boundaries (time, randomness, external worker
   determinism, audit binding). → `04_replay_substrate_boundaries.md`
5. APFS clonefile / phantom workspace as a possible future substrate
   layer. → `05_apfs_clonefile_phantom_workspace.md`
6. Concurrency / state-machine surfaces worth future TLA+ modeling.
   → `06_tla_plus_modeling_targets.md`
7. Open questions, ambiguities, and whether any of them is a true
   blocker for the design itself. → `07_open_questions_and_blockers.md`

## Hard non-scope (do not implement, do not design)

This package explicitly does **not** address:

- production-code rewrite of any service in `kernel/`
- UI, dashboards, project shell, lane orchestration ergonomics
- plugin system, extension API, marketplace surfaces
- multi-vendor routing, benchmark breadth, fairness scheduler
- distributed execution, cluster coordination, remote sync protocols
- release / packaging / notarization breadth
- new constitutional rules (none introduced; §3.10 honored)

## Constitutional anchors used

- §3.1 Truth sovereignty, §3.2 default deny, §3.3 replay honesty,
  §3.10 no new rules without physical evidence, §3.13 minimality at the
  hot path, §3.14 replacement-by-evidence
- §5 hardware baseline (Apple Silicon, macOS, anti-swap)
- §22.1, §22.2, §22.4, §22.5, §22.6, §22.11 contracts whose substrate
  surface is about to change
- §27 substrate strategy (mature substrates first; replacement only on
  evidence)
- §28 hardening loop and §30.3–§30.4 roadmap phases
- §31 sign-off honesty (no overclaiming)

## Design discipline

- Every recommendation is paired with: ownership boundary, evidence
  bar, failure mode, and replacement trigger.
- No recommendation broadens the eight-stage signable path.
- Where a substrate cannot meet a constitutional invariant honestly,
  this package says so explicitly rather than papering over it.
- Where a candidate exists but evidence to admit it does not, the
  candidate is recorded as **deferred-pending-evidence** under §27 and
  §3.14, not as a current obligation.

## Review-readiness statement

The package is honestly review-ready as a Phase-2 substrate *design*.
It is **not** review-ready as a Phase-2 substrate *implementation*, and
nothing in this package authorizes implementation work. Promotion from
design to implementation requires the evidence bars listed in each
section to be met under §28.
