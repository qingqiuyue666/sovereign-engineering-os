# External Execution Admission Boundary — Design Package

Status: **design-only**. No runtime code is introduced by this package.
No constitutional rules are added. No existing production module is
modified. No phase-2 substrate is admitted to implementation by this
package.

## Purpose

This package defines the **exact boundary** between the Python authority
surfaces of the Sovereign Engineering Operating System and any future
**bounded external executor** that may be introduced under the
phase-2 substrate strategy. The bounded executors in scope are:

- Wasmtime / WASI sandboxes (substrate B)
- Apple `Virtualization.framework` Linux guests (substrate A)
- Linux/KVM sidecars or remote workers (substrate C)
- APFS clonefile-backed phantom-workspace style bounded execution
  helpers (treated as a thin executor variant, not as a substrate)

The package answers nine questions, one per file, in the order they
appear in the brief:

1. Exact authority vs non-authority split
   → `01_authority_vs_non_authority_split.md`
2. Exact host/guest capability-broker boundary
   → `02_host_guest_capability_broker_boundary.md`
3. Exact quarantine / execution admission rules
   → `03_quarantine_execution_admission_rules.md`
4. Exact allowed I/O surfaces and forbidden mutation surfaces
   → `04_allowed_io_and_forbidden_mutation_surfaces.md`
5. Exact result-ingress rules (candidate material vs admitted truth;
   reject / downgrade / defer)
   → `05_result_ingress_rules.md`
6. Exact audit-binding and replay-minimum requirements for any
   external executor
   → `06_audit_binding_and_replay_minimum.md`
7. Exact dependency relationship to `phase2_promotion_gate`
   → `07_dependency_on_phase2_promotion_gate.md`
8. Explicit non-admission conditions
   → `08_explicit_non_admission_conditions.md`
9. Unresolved blockers vs recorded risks
   → `09_unresolved_blockers_vs_recorded_risks.md`

Foundational principles (default-deny posture, decision model,
constitutional anchors) live in `00_admission_boundary_principles.md`.

## Baseline (unchanged)

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
- `governance/implementation/v11_narrow_path_implementation_foundation.md`
- `governance/design/phase2_substrate/`
- `governance/design/phase2_promotion_gate/`

This package neither restarts architecture nor broadens scope. It does
not introduce new constitutional rules (§3.10 honored), no new AT or
INV identifiers, and no schema, contract, or receipt shape changes.
Every boundary defined here is a concrete application of existing v11
sections (§3.1, §3.2, §3.3, §3.11, §3.12, §3.13, §3.14, §5.5, §22.1,
§22.2, §22.4, §22.5, §22.6, §22.10, §22.11, §23.12, §23.13, §23.14,
§23.19, §27, §28, §29, §31).

## What this package is

A **boundary specification**. It tells the reviewer where the Python
control plane ends, where any future bounded executor begins, and what
must be true at the seam — no more, no less. It is the design that a
later admission PR (governed by `phase2_promotion_gate`) must conform
to, and the design that a reviewer can use to deny an admission PR
that does not.

## What this package is not

- It is **not** an authorization to build a sandbox, VM guest, sidecar,
  remote worker, or phantom workspace. Nothing here promotes any
  candidate listed in `phase2_substrate/` to implementation.
- It is **not** a substrate selection. Substrate choice and per-
  substrate evidence remain in `phase2_substrate/01_…` and
  `phase2_promotion_gate/02_…`.
- It is **not** a new contract. It imposes no runtime behavior, adds
  no AT/INV identifiers, and changes no schema.
- It is **not** a schedule. It has no calendar commitments.
- It is **not** a relaxation of `phase2_promotion_gate`. Every gate in
  that package continues to apply; this package adds a *boundary*
  conformance dimension on top of the existing gates.

## Hard non-scope (do not implement, do not design)

This package does **not** address and does **not** permit:

- production-code rewrite of any service in `kernel/`
- any change to schemas, contracts, receipts, or contract bindings
- any change to existing tests
- any change to phase-1 runtime modules (validation/quarantine, audit,
  capability, replay, classifier, etc.)
- UI, dashboards, project shell, lane orchestration ergonomics
- plugin system, extension API, marketplace surfaces
- multi-vendor routing, benchmark breadth, fairness scheduler
- distributed execution runtime, cluster coordination, remote sync
  protocols
- release / packaging / notarization breadth
- new constitutional rules
- new AT / INV identifiers
- new design directories outside this package

## Relationship to peer packages

- `phase2_substrate/` is the **map** of substrate candidates and what
  each could own.
- `phase2_promotion_gate/` is the **visa counter** that decides whether
  a candidate may cross from design to implementation, on a per-
  candidate evidence basis.
- This package — `external_execution_admission_boundary/` — is the
  **boundary** that any admitted executor (now or in the future) must
  honor regardless of which substrate it instantiates. It is substrate-
  shape-agnostic: a Wasmtime guest, an Apple-VM guest, a sidecar, and
  a clonefile-backed phantom workspace all face the same boundary
  rules; only the per-substrate evidence and entry criteria differ
  (those remain in `phase2_promotion_gate/`).

A candidate that has its `phase2_promotion_gate/` gate closed but
whose proposed implementation does not honor this boundary is denied
under §3.1 (truth sovereignty) and §3.11 (authority locality). The two
packages are complementary, not redundant; see file `07`.

## Design discipline

- **Default-deny.** No call, byte, or signal crosses the boundary
  unless an explicit rule in this package admits it.
- **Authority does not move.** No future executor is permitted to
  acquire any of the eight authority responsibilities listed in `01`.
- **Capabilities are consumed, never minted, by executors.** The
  capability broker is the *only* host-side mechanism that translates
  host-issued tokens into bounded effect handles inside an executor.
- **Result ingress is a re-validation, not a hand-off.** Bytes
  returned by an executor are *candidate material* until the host has
  re-validated, classified, and bound them; only then do they become
  admissible into the eight-stage signable path.
- **Audit and replay are host-only.** No executor writes to the audit
  ledger or mints `ReplayAnchor`. Period.
- **Honest downgrades.** Any dimension the executor cannot honestly
  satisfy routes through `replay_classifier`'s downgrade path before
  admission, never after.
- **No new contracts.** Where this package would otherwise want a new
  receipt field, it instead constrains the *use* of existing fields
  (e.g., `environment_fingerprint`, `version_tuple_hash`,
  `DriftEventRecord.dimension`) and defers any actual schema change to
  a separate, future governance increment.

## Review-readiness statement

This package is honestly review-ready as an **external execution
admission boundary design**. It is explicitly **not**:

- an authorization to introduce any external executor
- an authorization to modify any existing module to "prepare" for one
- a schedule or commitment
- a substitute for `phase2_promotion_gate/`'s per-candidate evidence
  bar
- a substitute for §31 sign-off

It is a tight, scoped, boundary specification whose only effect on the
repository is the presence of these twelve design files.
