# 06 — Relationship Between Claim Classes and Existing Surfaces

Scope: the exact relationship between the five claim classes and the
five surfaces the taxonomy touches:

1. the **replay classifier** (`kernel/replay/replay_classifier.py`,
   §22.5),
2. the **replay anchor** (`kernel/schemas/replay_anchor.schema.json`,
   §23.12),
3. the **evidence service**
   (`kernel/services/evidence_service.py`, §3.3 surfaces),
4. the **audit binding** (audit ledger and the
   `AuditRecord` surface, §22.1, §23.14),
5. the **external execution admission boundary**
   (`governance/design/external_execution_admission_boundary/`).

Constitutional anchors: §3.1, §3.2, §3.3, §3.11, §22.1, §22.5, §22.10,
§23.12, §23.14, §23.19, §27, §28, §31.

This file pins each surface's role with respect to the taxonomy. No
surface is modified by this design package.

---

## 1. Relationship to the replay classifier

### 1.1 Role

The classifier is the **sole author** of `replay_class_claim`. No
other component — caller, validator, substrate, executor, UI — may
assign a class. Callers may only *request* a class through
`ReplayClaimRequest.requested_class`; validators may only
*constrain* the admissible class via their policy (for example,
"this workload's ceiling is `semantic`").

### 1.2 Inputs the classifier takes

- `ReplayClaimRequest` (`requested_class`,
  `environment_fingerprint_hash`,
  `equivalence_proof_bundle_admitted`, identity triple).
- An `EvidenceView` protocol providing
  `has_sealed_revision`, `has_context_artifact`,
  `has_inference_artifact`, `required_artifact_ids`.

This file does not extend either input shape.

### 1.3 Outputs

- `ReplayClassification` (class + optional reason strings + required
  artifact ids).
- A `ReplayAnchor` dict constructed by `build_replay_anchor`
  conforming to `kernel/schemas/replay_anchor.schema.json`.

### 1.4 Taxonomy contract with the classifier

- The classifier's admitted class is always one of the five in
  `01`.
- The classifier never emits a class whose evidence in `03` is not
  met.
- The classifier's downgrade transitions stay inside the graph in
  `04`.
- The classifier's reasons stay inside the trigger table in `05`.
- The classifier does not edit an existing anchor; a new class
  requires a new anchor on a new revision (`06 §3`).

### 1.5 Phase-1 pin

Phase-1 code at `kernel/replay/replay_classifier.py` already honors
every rule in this file. This package pins the *meaning* of that
code. It does not change its behavior, its ordering, or its
reason strings.

---

## 2. Relationship to the replay anchor

### 2.1 Role

A `ReplayAnchor` is the receipt that carries the admitted class
into the signable path (§23.12). The anchor is minted exactly once
per `(project_id, task_id, root_revision_id)` at the class the
classifier decided, with the reason strings `03` requires.

### 2.2 Fields the taxonomy constrains (use, not shape)

- `replay_class_claim` — one of the five strings in `01`.
- `degradation_reason` — non-empty for `degraded`; non-empty for
  any class that arrived via downgrade from a strict higher
  request; absent for `exact` direct admissions; conditional on
  path for `unreplayable` (`03 §5`).
- `unreplayable_reason` — non-empty for `unreplayable`; absent
  otherwise.
- `environment_fingerprint_hash` — bound by audit (see §4 below).
- `version_tuple_hash` — bound by audit (see §4 below).
- `required_artifact_ids` — sourced from the evidence service's
  `required_artifact_ids` lookup (see §3 below).

### 2.3 Shape lock

No field on `ReplayAnchor` is added, removed, reshaped, or renamed
by this package. The schema at
`kernel/schemas/replay_anchor.schema.json` is the authority; this
package only constrains how its fields are populated.

### 2.4 Immutability

An anchor is immutable after mint. Class may not be edited. Reason
strings may not be rewritten. A revision whose anchor is `degraded`
today stays `degraded` forever for *that* revision; new evidence
produces a new anchor on a new revision.

---

## 3. Relationship to the evidence service

### 3.1 Role

The evidence service is the **sole source of truth** for artifact
presence used by the classifier's per-class evidence checks in `03`.
The `EvidenceView` protocol in the classifier names the four
lookups:

- `has_sealed_revision(root_revision_id)` → E-SEAL
- `has_context_artifact(task_id, root_revision_id)` → E-CTX
- `has_inference_artifact(task_id, root_revision_id)` → E-INF
- `required_artifact_ids(task_id, root_revision_id)` →
  `ReplayAnchor.required_artifact_ids`

### 3.2 Taxonomy contract with the evidence service

- Presence is authoritative: when the evidence service reports
  `False`, the classifier lowers per `05`.
- Partial presence is treated as absence at the taxonomy level;
  nuance lives in per-artifact receipts, not in a half-truth
  between classes.
- The evidence service never authors `replay_class_claim`. Its
  only taxonomy-relevant role is to answer presence lookups.

### 3.3 Not in scope for this file

This package does not add new evidence-service lookups, does not
add new artifact types, and does not change evidence-service
semantics. Where a new presence signal is wanted, it is a
governance increment elsewhere, not a taxonomy edit here.

---

## 4. Relationship to audit binding

### 4.1 Role

Audit binding (the §22.1 WAL path and `AuditRecord` pairs) is the
**sole source of truth** for the identity of the environment and
the version-tuple that a given claim is bound to. Specifically:

- `ReplayAnchor.environment_fingerprint_hash` is populated from the
  host-authored environment fingerprint bound into the producing
  session's `AuditRecord(enter)` (and, for external executors, the
  shim-policy digest per
  `external_execution_admission_boundary/06 §2–§4`).
- `ReplayAnchor.version_tuple_hash` is populated from the host-
  composed `version_tuple` at the signable-path G-7 point (see
  foundation §6; no new binding added here).
- The audit pair's durability and completeness are a precondition
  for the audit-minimum evidence item E-AUDIT-PAIR-OR-HOST-INTERNAL
  (`03 §2–§3`) and E-AUDIT-BINDING-COMPLETE (`03 §3`).

### 4.2 Taxonomy contract with audit binding

- The classifier reads audit-bound fields but never writes them;
  the anchor's `environment_fingerprint_hash` / `version_tuple_hash`
  come from audit, not from caller input.
- A durable-but-incomplete audit pair forces either reject (before
  classifier invocation) or `unreplayable` (`03 §5`, `05 §4.2`).
- A shim-policy drift in the audit binding forces a downgrade via
  `05 §2.4`.
- No executor may write to the audit ledger
  (`external_execution_admission_boundary/04 F-4`); the host is the
  sole author.

### 4.3 Not in scope for this file

This package does not add new `AuditRecord` fields, does not add
new audit-pair classes, and does not change the §22.1 write
protocol.

---

## 5. Relationship to the external execution admission boundary

### 5.1 Role

The external execution admission boundary governs what bytes and
signals cross from any future external executor into the host's
eight-stage signable path. A candidate crossing that boundary
becomes admissible only after ingress (`external_execution_admission_boundary/05`)
and only at the class the classifier then adjudicates.

### 5.2 Taxonomy contract with the boundary

- The boundary's **ingress rejections** (R-CAP, R-SCHEMA, R-TAINT,
  R-AUDIT-INCOH) happen **before** the classifier is invoked. A
  reject means no anchor at all, not an `unreplayable` anchor.
- The boundary's **ingress downgrades** (D-TIME, D-RAND,
  D-WORKER, D-AUDIT) produce `DriftEventRecord`s that the
  classifier's `05` trigger table then routes onto a `04`
  transition. The classifier, not the boundary, decides the
  admitted class.
- The boundary's **defers** produce either (a) a new anchor later
  on a new revision or (b) `unreplayable` on this revision per
  `05 §4.3`.
- Per-substrate class ceilings
  (`external_execution_admission_boundary/06 §7`) still hold:
  substrate C is capped at `semantic` absent a proof bundle that
  phase 1 does not admit.

### 5.3 Separation of concerns

- The boundary answers: "may this byte stream become candidate
  material at all?"
- The classifier answers: "at what class may this admitted bundle
  enter the anchor?"

The two packages compose; neither overrides the other. A bundle
that the boundary rejects never reaches the classifier. A bundle
that the boundary admits is classified per this taxonomy.

### 5.4 Executor posture never raises class

An executor's posture (shim policy, determinism mode) is *input* to
the classifier's decision; it can never *raise* the class. The
classifier adjudicates at the host side. No external executor
may mint, edit, or select a `replay_class_claim`
(`external_execution_admission_boundary/04 F-3`, repeated here for
completeness).

---

## 6. Per-surface authority summary

| Surface | Authority over class | Authority over reason strings | Authority over environment / version binding | Authority over evidence presence |
|---|---|---|---|---|
| Replay classifier | **sole author** | **sole author** | reads, never writes | reads, never writes |
| Replay anchor (receipt) | **carrier only** | **carrier only** | carrier only | carrier only |
| Evidence service | none | none | none | **sole source of truth** |
| Audit binding | none | none | **sole source of truth** | contributes audit-pair presence |
| External execution boundary | none | contributes drift reasons (ingress) | contributes via shim-policy digest | contributes via candidate inputs |

The classifier is the only component that authors class. The
anchor is the only receipt that carries class. The evidence
service is the only source of artifact presence. Audit is the
only source of environment / version binding. The boundary
constrains what becomes candidate but never adjudicates class.

---

## 7. Net statement

The taxonomy lives at the seam of these five surfaces. The
classifier decides, the anchor carries, the evidence service
informs presence, audit informs binding, and the boundary constrains
inbound candidates. No other component may speak the five class
names with authority. Every interaction named above is an existing
surface; none is introduced by this package.
