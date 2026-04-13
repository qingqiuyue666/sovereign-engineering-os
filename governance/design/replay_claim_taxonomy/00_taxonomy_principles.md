# 00 — Taxonomy Principles

Scope: the decision model for the replay claim taxonomy. This file
pins the invariants every later file in the package must honor, and
the constitutional anchors they rest on.

Constitutional anchors: §3.1, §3.2, §3.3, §3.10, §3.12, §22.5, §23.12,
§23.19, §24.2 (INV-010, INV-011), §31.

---

## 1. What a "claim class" is

A **claim class** is the single string the host writes into
`ReplayAnchor.replay_class_claim` (§23.12) for a given revision + task.
It is the system's honest, auditable posture about what a later replay
would be able to prove. It is not a quality score, not a priority, not
a policy knob, not a workflow stage.

The claim class is an output of the host-side `replay_classifier`
(§22.5). It is **never authored** by:

- the caller (the caller may only *request* a class);
- the validator (the validator may only *constrain* the admissible
  class for its workload);
- any external executor (`external_execution_admission_boundary/04`
  F-3 forbids executor-authored anchors);
- any future substrate under `phase2_substrate/` or
  `phase2_promotion_gate/`.

## 2. Closure

The taxonomy is closed at five classes:

    exact, diagnostic, semantic, degraded, unreplayable

See `01` for the pin to `kernel/schemas/replay_anchor.schema.json`'s
`replay_class_claim.enum` and `kernel/replay/replay_classifier.py`'s
`ReplayClass` enum.

Closure means:

- No sixth class may be introduced by this design package.
- No class may be renamed, split, or merged by this design package.
- Any proposal to extend or edit the set is a **constitutional
  change** (§3.10) that must route through the master plan, not
  through a design increment.

## 3. Default-deny on raise

A class may be raised above `unreplayable` only by producing the exact
evidence the target class requires in `03`. This is the inverse of a
schema default: the *default* posture for any claim whose evidence is
not proven is `unreplayable`. Raising to `degraded`, `semantic`,
`diagnostic`, or `exact` each has its own per-class evidence list that
must be fully satisfied.

Silence is lowering, never raising. A missing field, an unverified
digest, or an absent artifact is evidence shortfall and forces a
downgrade per `04` / `05`, never a "best-effort" admission.

## 4. Honest downgrade

Every downgrade traverses a path declared in `04` and carries the
reason required by `03`:

- A downgraded anchor has a non-empty `degradation_reason` string
  (§23.12 optional field).
- An anchor at `unreplayable` has a non-empty `unreplayable_reason`
  string (§23.12 optional field).
- Every dimension that forced a downgrade emits a `DriftEventRecord`
  (§23.19) naming the dimension and the reason.

No silent downgrade. No undocumented downgrade. No downgrade that
carries a success signal to the caller.

## 5. No in-band promotion

A `ReplayAnchor` is minted once, at the single classifier-decided
class, for a given `(project_id, task_id, root_revision_id)`. That
class is final for that revision. If new evidence later arrives (for
example, a previously missing `InferenceArtifact` is produced on a new
revision), the honest path is a **new anchor on a new revision** with
new evidence, not an edit of the prior anchor. See `06 §3`.

## 6. Classifier authority

The host-side `replay_classifier` is the sole authority that adjudicates
a class. The classifier's phase-1 behavior — recorded in
`kernel/replay/replay_classifier.py` with constitutional anchors
§22.5, §23.12, §24.1 (AT-013 / AT-032), and §24.2 (INV-010, INV-011)
— is the reference implementation of this taxonomy for phase 1 and is
not edited by this package. This package describes *what* the
classifier decides; it does not edit the *how*.

## 7. No new contracts

This package adds:

- no new schema
- no new enum value
- no new receipt field
- no new contract rule
- no new AT / INV identifier

Where the taxonomy wants a named field that does not exist, it
constrains the *use* of an existing field (for example, the existing
`degradation_reason` and `unreplayable_reason` strings on
`ReplayAnchor`, or the existing `dimension` / `reason` fields on
`DriftEventRecord`).

## 8. Truth sovereignty (§3.1), artifact conversion (§3.2), honest
   downgrade (§3.12)

The taxonomy is a direct application of three constitutional principles:

- **§3.1 Truth sovereignty.** A claim class is a truth statement about
  what a later replay can prove. Overclaiming violates §3.1.
- **§3.2 Artifact conversion rule.** Candidate material from
  executors and not-yet-re-validated inputs cannot raise a class; only
  host-admitted artifacts count as evidence toward a class.
- **§3.12 Honest downgrade.** Every class decision below the
  requested class must carry an honest, auditable reason.

## 9. Invariants this package owns

This package is the single source of truth for:

- the set of permitted class names (`01`);
- the meaning of each name (`02`);
- the evidence that admits each name (`03`);
- the downgrade graph between the names (`04`);
- the conditions that force automatic lowering (`05`);
- the names of surfaces that may mint, read, or constrain a class
  (`06`);
- the combinations that are always denied (`07`).

Any sentence anywhere else in the repository using one of the five
class names must be consistent with this package. This package does
not author constraints outside the taxonomy itself.

## 10. Design discipline — net statement

Five classes. One authority (the classifier). One mint point (the
anchor). One source of truth for artifact presence (the evidence
service). One source of truth for environment and version binding
(audit). Default-deny on raise. Honest downgrade or unreplayability
on every evidence shortfall. No sixth class. No rename. No silent
promotion. The taxonomy is tight by construction.
