# 09 — Honest Review-Readiness Statement

Scope: what this package **is** honestly review-ready for, and what
it **is not** — stated openly so a reviewer can approve the correct
thing and reject anything that would ask this package to authorize
more than it does.

Constitutional anchors: §3.10, §31.

---

## 1. What this package is review-ready as

This package is review-ready as a **replay claim taxonomy design**.
Specifically, a reviewer can inspect and approve or reject:

- the exact permitted set of five class names (`01`);
- the exact definition of each class (`02`);
- the exact per-class admission evidence (`03`);
- the exact permitted downgrade transitions between classes (`04`);
- the exact automatic-lowering triggers (`05`);
- the exact relationship between the five classes and the
  classifier, anchor, evidence service, audit binding, and
  external execution boundary (`06`);
- the exact forbidden claims and invalid combinations (`07`);
- the honest separation of blockers (none) from recorded semantic
  risks (eight) (`08`).

These are twelve design files and nothing else. The package's only
effect on the repository is the presence of those twelve files.

## 2. What this package is explicitly **not** review-ready as

This package is **not** review-ready as, and must not be interpreted
as:

- an authorization to change `kernel/schemas/replay_anchor.schema.json`
  (shape lock, §3.10);
- an authorization to change `kernel/replay/replay_classifier.py`
  (behavior lock, §3.10);
- an authorization to add a sixth class, rename, merge, or split
  any of the five (constitutional change per `07 §11`);
- an authorization to relax INV-010 (claim may not exceed captured
  evidence) or INV-011 (uncertified equivalence is never exact
  replay);
- an authorization to admit any phase-2 substrate (see
  `phase2_promotion_gate/`);
- an authorization to admit any external executor (see
  `external_execution_admission_boundary/`);
- an authorization to modify any phase-1 runtime module, schema,
  contract, receipt, test, UI, dashboard, plugin, or distributed
  execution runtime;
- a new AT or INV identifier;
- a schedule, calendar commitment, or release milestone;
- a substitute for §31 sign-off;
- a substitute for per-candidate evidence under
  `phase2_promotion_gate/`.

## 3. Conformance it creates

By being present, this package becomes a **conformance reference**:

- A future runtime change that edits `replay_class_claim` handling
  must cite the files in this package it conforms to (and,
  symmetrically, the specific rule its proposal violates or
  amends).
- A future design package that speaks about replay classes must be
  consistent with `02` (definitions), `03` (evidence), `04`
  (downgrade graph), `05` (lowering triggers), and `07` (forbidden
  shapes).
- A future boundary package, substrate package, or promotion-gate
  package that encodes class ceilings must be consistent with `02`
  and `06`.

Taxonomy nonconformance by a later proposal is itself sufficient
cause to deny that proposal.

## 4. Reviewer decision path

A reviewer of this package is asked to answer three questions:

1. Is the five-class set the right set for truth sovereignty (§3.1)
   and honest downgrade (§3.12), given the already-frozen
   `ReplayAnchor` schema and `ReplayClassifier` implementation?
2. Does each class's evidence list (`03`) cite only existing
   artifacts and existing fields, without introducing new shapes?
3. Is the recorded residual set in `08` honest — are any of the
   eight items secretly a blocker?

If yes/yes/no-they-are-risks, the package is approvable as-is.

If any `03` item references a field or artifact that does not
exist, that is a correction request.

If any `07` rule contradicts phase-1 classifier behavior, that is a
correction request.

If any residual in `08` is, on reflection, a blocker (i.e., the
package is internally inconsistent until it is resolved), that is a
rejection.

## 5. What approval of this package means

Approval of this package means:

- the five class names are the set the system uses;
- each class's definition, evidence, downgrade paths, lowering
  triggers, surface relationships, and forbidden shapes are as
  pinned here;
- future proposals will be evaluated for taxonomy conformance
  against this package.

Approval does **not** mean:

- any new runtime code;
- any new schema, contract, receipt, or test;
- any substrate or executor admission;
- any §31 sign-off;
- any calendar commitment.

## 6. Net statement

This package is a twelve-file taxonomy specification. It does not
touch runtime code, does not edit frozen surfaces, does not admit
substrates or executors, and does not anticipate any calendar. It
is honestly review-ready as design-only, with no unresolved
blockers and eight openly recorded semantic risks.
