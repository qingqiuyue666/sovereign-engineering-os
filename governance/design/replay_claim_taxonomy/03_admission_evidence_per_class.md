# 03 — Exact Admission Evidence Per Claim Class

Scope: the per-class evidence that admits each of the five classes.
This file is the per-class checklist. It describes **what must be
present** for the classifier to honestly arrive at a given class. It
does not describe *how* the classifier checks it — that lives in
`kernel/replay/replay_classifier.py` and §22.5.

Constitutional anchors: §3.3, §7.3, §22.5, §23.7 (ValidationReceipt),
§23.12 (ReplayAnchor), §23.17 (TaintRecord), §23.19 (DriftEventRecord),
§24.2 (INV-010, INV-011).

No new fields are added by this file. Every item on every checklist is
an existing, already-frozen artifact or an existing, already-frozen
field on an existing artifact.

---

## 1. Evidence required for `exact`

All of the following must be true at the moment the classifier is
invoked:

- **E-SEAL.** Sealed `Revision` (§23.11) for `root_revision_id` is
  present and durable (evidence service
  `has_sealed_revision == True`).
- **E-CTX.** `ContextArtifact` for `(task_id, root_revision_id)` is
  present (evidence service `has_context_artifact == True`).
- **E-INF.** `InferenceArtifact` for `(task_id, root_revision_id)`
  is present (evidence service `has_inference_artifact == True`).
- **E-ENV.** `environment_fingerprint_hash` is non-empty and was
  host-composed from the producing environment (audit-bound; see
  `06 §4`).
- **E-VER.** `version_tuple_hash` is non-empty and was host-
  composed on the same revision graph (audit-bound).
- **E-NO-DRIFT.** No unresolved `DriftEventRecord` (§23.19) names a
  binding dimension (time, randomness, worker, audit) for this
  `(task_id, root_revision_id)`.
- **E-NO-TAINT.** No `TaintRecord` (§23.17) propagates taint into
  the artifacts contributing to this anchor.
- **E-NO-PROOF-BUNDLE.** `equivalence_proof_bundle_admitted` is
  **False**. INV-011 forbids equivalence-proof substitution under
  `exact`. Phase 1 does not admit proof bundles at all; see
  `replay_classifier.py` lines 121–148.
- **E-REQUEST.** The classifier was asked for `exact` (and not,
  for example, `diagnostic` with a higher posture).

**Receipt shape invariants for `exact`.**

- `ReplayAnchor.replay_class_claim == "exact"`
- `ReplayAnchor.degradation_reason` absent / empty
- `ReplayAnchor.unreplayable_reason` absent / empty

Any single missing item in E-SEAL / E-CTX / E-INF / E-ENV / E-VER /
E-NO-DRIFT / E-NO-TAINT forces the automatic lowering in `05 §2`.
E-NO-PROOF-BUNDLE failure forces the downgrade defined in `05 §2.5`.

---

## 2. Evidence required for `diagnostic`

All of the following must be true:

- **E-SEAL.** Sealed revision present.
- **E-CTX.** `ContextArtifact` present for `(task_id,
  root_revision_id)`.
- **E-AUDIT-PAIR-OR-HOST-INTERNAL.** Either (a) the audit pair
  (enter/exit) for any external-executor session contributing to
  the run is durable and complete per
  `external_execution_admission_boundary/06 §5`, or (b) the run is
  host-internal and the §22.1 WAL posture for the producing stage
  is met.
- **E-ENV.** `environment_fingerprint_hash` populated host-side.
- **E-VER.** `version_tuple_hash` populated host-side.
- **E-REQUEST.** The classifier was asked for `diagnostic`, or
  arrived at `diagnostic` by downgrade from `exact`.

`InferenceArtifact` is **not** required for `diagnostic` when the
validator's decision trace does not depend on it. When it *is*
required by the validator's policy and missing, the classifier
downgrades further to `degraded` per `04` / `05`.

**Receipt shape invariants for `diagnostic`.**

- `ReplayAnchor.replay_class_claim == "diagnostic"`
- `ReplayAnchor.degradation_reason` may be absent (direct claim) or
  populated (downgrade from `exact` with a named reason).
- `ReplayAnchor.unreplayable_reason` absent / empty.

---

## 3. Evidence required for `semantic`

All of the following must be true:

- **E-SEAL.** Sealed revision present.
- **E-CTX.** `ContextArtifact` present.
- **E-AUDIT-BINDING-COMPLETE.** Enter/exit audit pair (or host-
  internal equivalent) durable and complete.
- **E-HOST-REVALIDATION.** Host re-validation of returned /
  produced artifacts has succeeded; a `ValidationReceipt` (§23.7)
  is present where the validator produces one.
- **E-ENV / E-VER.** Populated host-side.
- **E-REQUEST.** The classifier was asked for `semantic`, or
  arrived at `semantic` by downgrade from `exact` or `diagnostic`
  per `04`.

Worker determinism is **not** required for `semantic` (hence
substrate C admissibility per
`external_execution_admission_boundary/06 §7.3`).

**Receipt shape invariants for `semantic`.**

- `ReplayAnchor.replay_class_claim == "semantic"`
- `ReplayAnchor.degradation_reason` may be absent (direct claim) or
  populated (downgrade).
- `ReplayAnchor.unreplayable_reason` absent / empty.

---

## 4. Evidence required for `degraded`

All of the following must be true:

- **E-SEAL.** Sealed revision present.
- **E-AUDIT-MIN.** Audit binding is complete enough to mint an
  anchor at all (i.e., an enter/exit pair is durable and complete
  where applicable; a `ReplayAnchor` can be honestly minted).
- **E-DOWNGRADE-REASON.** `ReplayAnchor.degradation_reason` is
  non-empty, and names the dimension that fell short.
- **E-DRIFT-RECORD.** At least one `DriftEventRecord` (§23.19) is
  present for this `(task_id, root_revision_id)`, naming the same
  dimension and reason.
- **E-REQUEST-OR-DOWNGRADE.** Either the caller asked for
  `degraded` directly (see `replay_classifier.py` lines 182–188),
  or the classifier downgraded to `degraded` via a permitted path
  in `04`.

**Receipt shape invariants for `degraded`.**

- `ReplayAnchor.replay_class_claim == "degraded"`
- `ReplayAnchor.degradation_reason` present and non-empty.
- `ReplayAnchor.unreplayable_reason` absent / empty.

---

## 5. Evidence required for `unreplayable`

At least one of the following must be true:

- **E-SEAL-ABSENT.** Sealed revision is *not* present
  (`has_sealed_revision == False`;
  see `replay_classifier.py` lines 98–104).
- **E-CALLER.** The caller declared `unreplayable` explicitly.
- **E-AUDIT-UNRECOVERABLE.** The audit pair for any contributing
  executor session is durable-but-incomplete, and the missing
  field(s) are in the minimum list pinned by
  `external_execution_admission_boundary/06 §5.3` (which forces
  reject or, where the host policy admits, `unreplayable`).
- **E-INGRESS-UNAMBIGUOUS-DEFER.** Ingress of candidate material
  terminated in a defer that no new evidence can close on this
  revision (see `05 §4.3`).

And in all cases:

- **E-UNREPLAYABLE-REASON.** `ReplayAnchor.unreplayable_reason` is
  non-empty and names the reason.

**Receipt shape invariants for `unreplayable`.**

- `ReplayAnchor.replay_class_claim == "unreplayable"`
- `ReplayAnchor.unreplayable_reason` present and non-empty.
- `ReplayAnchor.degradation_reason` **may** be absent or present.
  An `unreplayable` anchor that also carries a `degradation_reason`
  is admissible only when the unreplayability was reached by
  downgrade-then-unreplayable through the transitions in `04`.

---

## 6. Evidence surfaces (where each item lives)

| Evidence item | Owning surface | Receipt field / state |
|---|---|---|
| E-SEAL | evidence service / revision store | `has_sealed_revision` |
| E-CTX | evidence service / context service | `has_context_artifact` |
| E-INF | evidence service / inference service | `has_inference_artifact` |
| E-ENV | audit binding | `ReplayAnchor.environment_fingerprint_hash` |
| E-VER | audit binding | `ReplayAnchor.version_tuple_hash` |
| E-NO-DRIFT | drift ledger / §23.19 | absence of `DriftEventRecord` on binding dimension |
| E-NO-TAINT | taint ledger / §23.17 | absence of propagated `TaintRecord` |
| E-NO-PROOF-BUNDLE | classifier request | `ReplayClaimRequest.equivalence_proof_bundle_admitted == False` |
| E-AUDIT-PAIR / E-AUDIT-BINDING-COMPLETE | audit ledger / §22.1 | enter/exit pair durable and complete |
| E-HOST-REVALIDATION | validator / §23.7 | `ValidationReceipt` present |
| E-DOWNGRADE-REASON | classifier output | `ReplayAnchor.degradation_reason` |
| E-DRIFT-RECORD | drift ledger | `DriftEventRecord` for the named dimension |
| E-UNREPLAYABLE-REASON | classifier output | `ReplayAnchor.unreplayable_reason` |

All items are *uses* of existing surfaces. No new surface is
introduced.

---

## 7. Evidence coverage rule

The classifier admits the **highest** class whose evidence is fully
present. A class is "admitted" when every item on its checklist is
true. The classifier never admits a class for which any checklist
item is absent or negative; the automatic-lowering rules in `05`
name the exact transition.

## 8. Net statement

Each class has a pinned, finite, auditable evidence list. Every
item on every list is an existing field or existing artifact. No
item is optional. No item can be waived by caller request. Raising
a class above what the evidence supports is forbidden (INV-010 /
`07 §7`); substituting equivalence for sealed inputs is forbidden
(INV-011 / `07 §8`). The five lists above are the single source of
truth for what each class *means to have earned*.
