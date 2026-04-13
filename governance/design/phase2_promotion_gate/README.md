# Phase-2 Promotion Gate — Design Package

Status: **design-only**. No runtime code is introduced by this package.
No constitutional rules are added. No existing production module is
modified. No implementation of anything in `governance/design/phase2_substrate/`
is authorized by this package.

## Purpose

This package defines the **exact evidence bar** that must be met before
any phase-2 substrate work listed in `governance/design/phase2_substrate/`
is allowed to leave the design shelf and become implementation work.

It answers seven questions, one per file:

1. Exact prerequisites for promoting phase-2 from design to
   implementation as a whole
   → `01_phase2_design_to_implementation_prerequisites.md`
2. Exact entry criteria for each execution substrate candidate
   (Apple `Virtualization.framework`, Wasmtime/WASI, Linux/KVM sidecar
   or remote worker)
   → `02_execution_substrate_entry_criteria.md`
3. Exact entry criteria for Rust downshift candidates (R-1…R-6 from
   `phase2_substrate/03_rust_downshift_candidates.md`)
   → `03_rust_downshift_entry_criteria.md`
4. Exact replay / determinism / audit-binding evidence required before
   any substrate is promoted
   → `04_replay_determinism_audit_binding_evidence.md`
5. Exact TLA+ admission targets (TLA-1…TLA-7) and their preconditions
   → `05_tla_plus_admission_targets_and_preconditions.md`
6. Explicit non-admission conditions — when phase-2 implementation is
   forbidden even if the roadmap looks attractive
   → `06_explicit_non_admission_conditions.md`
7. Unresolved risks that remain blockers vs risks that are merely
   recorded (and why)
   → `07_unresolved_blockers_vs_recorded_risks.md`

Foundational principles (default-deny posture, decision model) live
in `00_promotion_gate_principles.md`.

## Baseline (unchanged)

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
- `governance/implementation/v11_narrow_path_implementation_foundation.md`
- `governance/design/phase2_substrate/` (the design package this gate
  governs)

This package neither restarts architecture nor broadens scope. It does
not introduce new constitutional rules (§3.10 honored). Every
promotion decision defined here is a concrete application of §27
(substrate strategy: mature first, replacement on evidence), §28
(hardening loop), §3.14 (replacement-by-evidence), and §31 (sign-off
honesty).

## Hard non-scope (do not implement, do not design)

This package does **not** address and does **not** permit:

- production-code rewrite of any service in `kernel/`
- UI, dashboards, project shell, lane orchestration ergonomics
- plugin system, extension API, marketplace surfaces
- multi-vendor routing, benchmark breadth, fairness scheduler
- distributed execution, cluster coordination, remote sync protocols
- release / packaging / notarization breadth
- new constitutional rules
- new AT/INV identifiers
- changes to existing schema, contract, or receipt shapes

## Relationship to `phase2_substrate/`

`phase2_substrate/` describes *what* the candidate substrates are and
*why* each one could earn its place. This package describes *when* any
of them becomes admissible and *what evidence* must exist first. The
two packages are complementary: the substrate package is the map, this
package is the visa counter.

A substrate candidate or a Rust downshift candidate that is listed
under `phase2_substrate/` is not, by virtue of being listed, eligible
for implementation. Eligibility is governed by this package.

## Design discipline

- **Default-deny.** Absent explicit gate closure for a candidate, the
  candidate is not admitted. Silence is never an admission.
- **Per-candidate gates.** Promotion is per-substrate and per-candidate,
  never a phase-wide flip.
- **Evidence artifacts named.** Each gate names the concrete artifact
  that must exist (a measurement, a receipt class, a replay trace, a
  TLA+ counterexample status, a failure record).
- **Honest downgrades.** Where a substrate cannot meet a dimension,
  the gate requires `replay_classifier`'s downgrade path to be in
  place before the substrate is admitted — not after.
- **Irreversibility noted.** Where admission is hard to reverse
  (audit ledger wiring, capability broker), the gate adds a
  reversibility review step.
- **No new constitutional rules.** Every requirement in this package
  resolves to an existing v11 section.

## Review-readiness statement

This package is honestly review-ready as a **promotion-gate design**.
It is explicitly **not**:

- an authorization for any phase-2 substrate to be implemented
- a schedule
- a commitment that every listed candidate will eventually pass its
  gate
- a replacement for `phase2_substrate/`

It is a tight, scoped, evidence-bar specification whose only effect on
the repository is the presence of these seven design notes plus the
manifest.
