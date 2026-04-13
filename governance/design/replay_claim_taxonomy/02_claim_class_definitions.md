# 02 — Exact Claim Class Definitions

Scope: the exact definition of each of the five permitted claim
classes. Every definition is a single, falsifiable statement about
what a later replay can honestly prove.

Constitutional anchors: §3.2 (artifact conversion rule), §3.3
(admission gating), §3.12 (honest downgrade), §22.5 (replay fidelity
contract), §23.12 (ReplayAnchor), §24.2 (INV-010, INV-011).

The evidence that admits each class lives in `03`. This file defines
each class semantically; it does not re-list the per-class evidence
tables.

---

## 1. `exact`

**Definition.** A replay reproduces the same authority artifacts
byte-for-byte — for the specific `(project_id, task_id,
root_revision_id)` the anchor names — from the same sealed inputs,
the same host-bound environment, and the same host-issued
randomness/time/worker-determinism posture that originally produced
them.

**What it asserts.**

- Sealed revision (§23.11) present and identical.
- `ContextArtifact` (§23.x / context service) present for the
  `(task_id, root_revision_id)` pair.
- `InferenceArtifact` (§23.x / inference service) present for the
  same pair.
- `environment_fingerprint` bound into the anchor matches the
  producing environment (no shim-policy drift, no clock-policy
  drift, no PRNG drift, no worker-identity drift).
- `version_tuple_hash` present and host-composed from the same
  revision graph.
- No `DriftEventRecord` (§23.19) for this `(task_id,
  root_revision_id)` names an unresolved drift dimension.
- `degradation_reason` is absent (empty / not present). An anchor
  at `exact` with a non-empty `degradation_reason` is invalid
  (`07 §1`).

**What it does not assert.**

- It does not assert performance equivalence, timing equivalence, or
  resource-usage equivalence.
- It does not assert that a *different* revision will replay the
  same bytes; it asserts only this revision.
- It does not assert equivalence under any "proof bundle" that
  substitutes different inputs for the sealed ones. INV-011
  forbids that. Phase-1 does not admit equivalence-proof bundles
  (foundation §6; see also `replay_classifier.py` lines 121–148).

**Invariant.** `exact` is the *only* class that is admissible when
**all** of the following are true:

- all required artifacts are present (evidence service);
- no shim-policy drift (audit binding);
- no taint propagated to candidate material (see `05 §3`);
- no active `DriftEventRecord` on any dimension for this
  `(task_id, root_revision_id)`.

If any of those is untrue, the admissible class is one of
`diagnostic`, `semantic`, `degraded`, or `unreplayable` per `04` and
`05`.

---

## 2. `diagnostic`

**Definition.** A replay reproduces the decision-relevant signals
that the original run produced — enough for a reviewer or §31 sign-
off to reconstruct *what the system decided and why* — but not
necessarily the same authority bytes.

**What it asserts.**

- Sealed revision present.
- Audit pair (enter/exit, where applicable) durable on the §22.1
  WAL path.
- Sufficient artifact presence to reconstruct the decision trace
  (for example, `ContextArtifact` present; the inference artifact
  *may* be absent for a diagnostic-only validator that does not
  require one).
- `environment_fingerprint` populated host-side.
- The classifier was given the requested class `diagnostic` or
  arrived at `diagnostic` by downgrade from `exact` per `04`.

**What it does not assert.**

- It does not assert byte-exact artifact reproduction.
- It does not assert that rerunning the validator will produce the
  same receipt contents; it asserts the *decision trace* can be
  reconstructed from audit + evidence.

**When admissible.** When the evidence in `03 §2` is fully present
and the classifier was asked for `diagnostic` or downgraded from
`exact` because the exact-class evidence in `03 §1` was not met but
the diagnostic-class evidence is.

---

## 3. `semantic`

**Definition.** A replay reproduces the same *semantic outcome* —
the same decision class the validator adjudicates — but not
necessarily the same bytes, and not necessarily the same
decision-relevant internal trace. The classifier admits `semantic`
when host re-validation of the relevant artifacts succeeds and
audit binding is complete, even if worker-determinism or some
decision-trace detail is not host-bindable.

**What it asserts.**

- Sealed revision present.
- Audit binding complete (enter/exit pair durable, or, for host-
  internal workloads, the applicable §22.1 durability posture).
- Host re-validation of returned / produced artifacts has
  succeeded.
- The validator's semantic contract is satisfied.

**What it does not assert.**

- It does not assert byte-exact reproduction.
- It does not assert a reconstructable diagnostic trace beyond the
  semantic contract.
- It does not assert worker-determinism (hence substrate C's
  default per
  `external_execution_admission_boundary/06 §7.3`).

**Relationship to substrate C.** For Linux/KVM sidecars and remote
workers, `semantic` is the default admissible ceiling. Raising above
`semantic` for substrate-C-produced artifacts requires a signed,
audited equivalence-proof bundle, which phase 1 does not admit
(INV-011 applies).

---

## 4. `degraded`

**Definition.** A replay yields *less* than its requested class
because at least one evidence dimension fell short, and the
classifier honestly admitted at a lower class with a named
`degradation_reason`. `degraded` is the class the system uses when
the honest answer is "we admit this, but on notice."

**What it asserts.**

- Sealed revision present.
- Audit binding complete enough to mint an anchor at all.
- At least one named, recorded degradation reason
  (`ReplayAnchor.degradation_reason` non-empty).
- A `DriftEventRecord` (§23.19) is written naming the dimension
  that fell short and the reason.
- The caller-requested class was strictly above `degraded` in the
  ordering of `01 §3`, and the classifier downgraded per `04`.

**What it does not assert.**

- It does not assert any *positive* fidelity guarantee. `degraded`
  is a negative shape: "something was short; here is what and
  why."
- It does not assert that the same run will re-downgrade
  identically on a later replay; the downgrade reason is pinned to
  this anchor only.

**When admissible.** When exactly one or more named dimensions
failed the target-class evidence check in `03 §1–§3` and none of the
automatic-lowering triggers in `05 §2–§4` forced `unreplayable`.

**Canonical examples.**

- Exact requested; `InferenceArtifact` missing → `degraded` with
  `degradation_reason = "missing context or inference artifact; exact replay refused"`
  (this is the phase-1 classifier's exact string; see
  `replay_classifier.py` line 123).
- Exact requested with `equivalence_proof_bundle_admitted=True` →
  `degraded` with
  `degradation_reason = "equivalence proof bundle not admissible in phase 1"`
  (INV-011; see `replay_classifier.py` lines 140–148).
- Semantic requested; `ContextArtifact` missing → `degraded` with
  `degradation_reason = "missing context artifact"` (see
  `replay_classifier.py` lines 167–172).

---

## 5. `unreplayable`

**Definition.** A replay cannot be attempted at any of the four
stronger classes because the minimum preconditions for *any* honest
replay claim are not present.

**What it asserts.**

- `ReplayAnchor.unreplayable_reason` is non-empty and names the
  reason.
- Either the sealed revision is missing, the audit binding cannot
  be made complete, or the caller explicitly requested
  `unreplayable`.

**What it does not assert.**

- It does not assert that the work produced no artifacts; it
  asserts only that a later replay cannot honestly reproduce them.
- It does not assert that the revision is invalid for other
  purposes; authority artifacts on the revision may still be
  correct, they are merely not replayable.

**When admissible.** When either:

- `has_sealed_revision(root_revision_id) == False`
  (`replay_classifier.py` lines 98–104), or
- the caller declared `unreplayable` (`replay_classifier.py`
  lines 190–196), or
- any of the automatic-lowering triggers in `05 §4` fires an
  unreplayable outcome (for example, audit pair durable-but-
  incomplete forces reject-or-unreplayable per
  `external_execution_admission_boundary/06 §5.3`).

**Difference from an absent anchor.** `unreplayable` is still an
anchor. An *absent* anchor is a different state — no claim at all
— and is governed by the signable-path orchestrator, not by this
taxonomy. See `07 §6`.

---

## 6. Class distinction sheet (at a glance)

| Class          | Byte-exact artifacts | Decision trace | Semantic equivalence | Audit bracket | Why this class is used |
|----------------|----------------------|----------------|----------------------|---------------|------------------------|
| `exact`        | yes                  | yes            | yes                  | yes           | full evidence closure  |
| `diagnostic`   | no                   | yes            | possibly             | yes           | enough to reconstruct decision |
| `semantic`     | no                   | no             | yes                  | yes           | host re-validation succeeded |
| `degraded`     | *partial or no*      | *partial*      | *partial*            | yes           | at least one dimension short |
| `unreplayable` | no                   | no             | no                   | optional      | min preconditions absent |

This table is a summary. The authoritative definitions are §1–§5
above; the authoritative evidence lists are in `03`.

---

## 7. Invariants across the five definitions

- An anchor at `exact` with a non-empty `degradation_reason` is
  invalid (`07 §1`).
- An anchor at `exact` with any active `DriftEventRecord` on a
  binding dimension for the same `(task_id, root_revision_id)` is
  invalid (`07 §2`).
- An anchor at `unreplayable` with `unreplayable_reason` empty is
  invalid (`07 §3`).
- An anchor at `degraded` with both `degradation_reason` absent
  **and** no `DriftEventRecord` for any dimension is invalid
  (`07 §4`).
- An anchor that claims a class strictly above the class the
  classifier would have produced given the present evidence is a
  silent class raise and is forbidden (`07 §7`).
