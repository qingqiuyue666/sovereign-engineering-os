# Replay Claim Taxonomy — Design Package

Status: **design-only**. No runtime code is introduced by this package.
No constitutional rules are added. No schema, contract, receipt, test,
or phase-1 runtime module is modified. No substrate or executor is
admitted to implementation by this package.

## Purpose

This package defines the **exact permitted claim classes** the Sovereign
Engineering Operating System uses when it talks about replayability,
determinism, evidence sufficiency, and execution-result trust. It pins
the taxonomy — the class set, the per-class definitions, the per-class
admission evidence, the permitted downgrade transitions, the auto-
lowering triggers, the relationship to existing surfaces, and the
forbidden claims — so that no stage, receipt, validator, substrate, or
external executor can make up a sixth class, rename a class, blur two
classes, raise a class silently, or admit a class without its declared
evidence.

The class set itself is not invented here. It is already pinned in two
frozen surfaces of phase-1:

- `kernel/schemas/replay_anchor.schema.json`
  (`replay_class_claim.enum`)
- `kernel/replay/replay_classifier.py`
  (`ReplayClass` enum: `EXACT`, `DIAGNOSTIC`, `SEMANTIC`, `DEGRADED`,
  `UNREPLAYABLE`)

This package **constrains how those classes are used**. It does not
add, remove, rename, or reorder them.

## The nine questions, one file each

1. Exact allowed claim classes
   → `01_claim_classes.md`
2. Exact definition of each claim class
   → `02_claim_class_definitions.md`
3. Exact admission evidence required per claim class
   → `03_admission_evidence_per_class.md`
4. Exact downgrade paths between claim classes
   → `04_downgrade_paths.md`
5. Exact conditions under which a claim must be lowered automatically
   → `05_automatic_lowering_conditions.md`
6. Exact relationship between claim classes and replay classifier,
   replay anchor, evidence service, audit binding, external execution
   boundary
   → `06_relationship_to_existing_surfaces.md`
7. Exact forbidden claims and invalid combinations
   → `07_forbidden_claims_and_invalid_combinations.md`
8. Unresolved blockers vs recorded semantic risks
   → `08_unresolved_blockers_vs_recorded_risks.md`
9. Honest review-readiness statement
   → `09_review_readiness_statement.md`

Foundational principles (default-deny on raise, honest downgrade,
closure over five classes) live in `00_taxonomy_principles.md`.

## Baseline (unchanged)

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
- `governance/implementation/v11_narrow_path_implementation_foundation.md`
- phase-1 narrow-path implementation and hardening increments
  (merged; includes `kernel/replay/replay_classifier.py` and
  `kernel/schemas/replay_anchor.schema.json`)
- `governance/design/phase2_substrate/`
- `governance/design/phase2_promotion_gate/`
- `governance/design/external_execution_admission_boundary/`

This package does not broaden scope, does not restart architecture, and
does not introduce new constitutional rules (§3.10 honored). It adds no
new AT or INV identifiers, no new schemas or contracts, no runtime
module changes.

## What this package is

A **taxonomy specification**. It tells the reviewer exactly which claim
classes exist, what each means, what evidence each requires, how one
class decays to another, and how the classes connect to the classifier,
the anchor, the evidence service, the audit ledger, and the external
execution boundary. It is the shared vocabulary that §31 sign-off, the
classifier's downgrade path, and any future admission PR must speak.

## What this package is not

- It is **not** an authorization to change the `ReplayAnchor` schema
  or the `ReplayClass` enum. It constrains *use*, not *shape*.
- It is **not** an authorization to add a new claim class (e.g.,
  `provisional`, `attested`, `partial`). See `07`.
- It is **not** an authorization to relax `INV-010` (claim may not
  exceed captured evidence) or `INV-011` (uncertified equivalence is
  never exact replay).
- It is **not** a substrate admission or an executor admission. Those
  remain governed by `phase2_promotion_gate/` and
  `external_execution_admission_boundary/`.
- It is **not** a change to `replay_classifier`'s step ordering; the
  classifier's phase-1 ordering stands and is cited as-is.
- It is **not** a new contract, receipt field, or AT / INV identifier.
- It is **not** a schedule or calendar commitment.
- It is **not** a substitute for §31 sign-off.

## Hard non-scope (do not implement, do not design)

This package does **not** address and does **not** permit:

- any modification of `kernel/` modules
- any change to schemas, contracts, receipts, or contract bindings
- any change to existing tests
- any change to phase-1 runtime modules (evidence service, audit,
  capability, replay classifier, signable-path orchestrator, etc.)
- UI, dashboards, project shell
- plugin system, extension API, marketplace surfaces
- distributed execution runtime, cluster coordination, remote sync
  protocols
- release / packaging / notarization breadth
- new constitutional rules
- new AT / INV identifiers
- new design directories outside this package

## Relationship to peer packages

- `phase2_substrate/` is the **map** of substrate candidates.
- `phase2_promotion_gate/` is the **visa counter** that decides whether
  a candidate may cross from design to implementation.
- `external_execution_admission_boundary/` is the **boundary** any
  admitted executor must honor.
- This package — `replay_claim_taxonomy/` — is the **vocabulary** that
  all three peers already speak. It does not change them; it pins the
  shared definitions they already rely on.

A package-level invariant: any sentence anywhere in the repository that
uses one of the five class names must be consistent with the
definitions in `02`, the evidence in `03`, and the forbidden-claims
rules in `07`. This package is the single source of truth for that
consistency.

## Design discipline

- **Closure at five.** The taxonomy is closed. Exactly five classes:
  `exact`, `diagnostic`, `semantic`, `degraded`, `unreplayable`. A
  sixth class is a constitutional change (§3.10), not a design edit.
- **Default-deny on raise.** A class may only be raised by producing
  the exact evidence `03` requires. Silence is lowering, never raising.
- **Honest downgrade.** Any dimension the evidence does not cover must
  route through a declared downgrade path from `04` before admission,
  never after.
- **No in-band promotion.** Admission of a class into a `ReplayAnchor`
  does not later upgrade. Upgrades require a new anchor on a new
  revision with new evidence, not a rewrite.
- **Classifier authority.** The host-side `replay_classifier` is the
  sole decider of class. No executor, no validator, no caller may
  override a classifier decision; callers may only *request* a class,
  which the classifier may honor or lower.
- **No new contracts.** Where this package would otherwise want a new
  receipt field or enum value, it instead constrains the *use* of the
  existing frozen `replay_class_claim` enum and the existing
  `degradation_reason` / `unreplayable_reason` string fields.

## Review-readiness statement

This package is honestly review-ready as a **replay claim taxonomy
design**. It is explicitly **not**:

- an authorization to change the `ReplayAnchor` schema or enum set
- an authorization to modify `replay_classifier`
- a substrate or executor admission
- a new AT / INV / schema / contract / receipt shape
- a substitute for §31 sign-off or for `phase2_promotion_gate/`

It is a tight, scoped, taxonomy specification whose only effect on the
repository is the presence of these twelve design files.
