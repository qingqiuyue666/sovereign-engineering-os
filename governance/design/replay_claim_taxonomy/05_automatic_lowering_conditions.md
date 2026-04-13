# 05 — Exact Conditions Under Which a Claim Must Be Lowered Automatically

Scope: the conditions that force the classifier to admit a class
strictly below the caller-requested class. This file is the trigger
table. The permitted transitions (the graph) live in `04`. The per-
class evidence checklists (what must be true for each class) live in
`03`.

Constitutional anchors: §3.3, §3.12, §22.5, §22.11 (taint
propagation), §23.12, §23.17, §23.19, §24.2 (INV-010, INV-011).

This file describes behavior the classifier already honors in phase
1 (see `kernel/replay/replay_classifier.py`) and pins the *meaning* of
that behavior into a single table. No new runtime behavior is
introduced.

---

## 1. General rule

The classifier admits the **highest** class whose evidence in `03` is
fully present. If the caller-requested class's evidence is not fully
present, the classifier lowers to the highest class whose evidence
*is* present, along a transition declared in `04`.

Every automatic lowering:

- writes the named reason into `ReplayAnchor.degradation_reason`
  (for `degraded` or any class lowered from a strict higher
  request);
- writes `ReplayAnchor.unreplayable_reason` when the terminal class
  is `unreplayable`;
- emits at least one `DriftEventRecord` (§23.19) naming the
  dimension that forced the lowering, unless the lowering is from
  sealed-revision-absent (which writes `unreplayable_reason`
  directly; see §4.1).

---

## 2. Triggers that lower from `exact`

### 2.1 Sealed revision absent

Condition: `evidence.has_sealed_revision(root_revision_id) ==
False`.

Forced outcome: `exact → unreplayable`,
`unreplayable_reason = "sealed revision not found"` (pinned by
`replay_classifier.py` lines 98–104).

### 2.2 Context artifact absent

Condition: `has_context_artifact == False` under a requested class
of `exact`.

Forced outcome: `exact → degraded` with
`degradation_reason = "missing context or inference artifact; exact replay refused"`
(phase-1 behavior; see `replay_classifier.py` lines 121–135).
`DriftEventRecord` emitted naming the context dimension.

### 2.3 Inference artifact absent

Condition: `has_inference_artifact == False` under a requested
class of `exact`.

Forced outcome: same as §2.2 (phase-1 rule: both shortfalls route
through the same reason string).

### 2.4 Binding-dimension shortfall under `exact`

Condition: one or more of the four binding dimensions (time,
randomness, worker determinism, audit binding) is short of the
`exact` minimum (see
`external_execution_admission_boundary/06 §2–§5` for the external-
executor case, or the host-internal analogue for phase-1 host work).

Forced outcome: lowering to the highest class whose binding
posture is met, via a `04 §2` transition:

- `exact → diagnostic` when only the decision-trace-level binding
  is met;
- `exact → semantic` when only the validator's semantic contract
  is met;
- `exact → degraded` when a binding dimension is short and the
  validator's policy admits `degraded` with a named
  `degradation_reason`;
- `exact → unreplayable` when the binding shortfall fails the
  audit-minimum pair (`03 §5` / §4.1 below).

In all cases a `DriftEventRecord` names the shortfall dimension.

### 2.5 Equivalence proof bundle asserted under `exact`

Condition: `ReplayClaimRequest.equivalence_proof_bundle_admitted ==
True`.

Forced outcome: `exact → degraded` with
`degradation_reason = "equivalence proof bundle not admissible in phase 1"`
(INV-011; pinned by `replay_classifier.py` lines 140–148). This
downgrade fires even when all other evidence for `exact` is
present.

### 2.6 Taint propagated to contributing artifacts

Condition: a `TaintRecord` (§23.17) propagates into any artifact
contributing to this anchor.

Forced outcome: if the ingress refused the taint outright
(`external_execution_admission_boundary/05 G-5`, `R-TAINT`), no
anchor is minted. If the ingress admitted the candidate with the
`TaintRecord` bound, the classifier lowers per validator policy —
typically `exact → degraded` with the taint dimension named.

---

## 3. Triggers that lower from `diagnostic` or `semantic`

### 3.1 Context artifact absent under `semantic`

Condition: `has_context_artifact == False` under a requested class
of `semantic`.

Forced outcome: `semantic → degraded` with
`degradation_reason = "missing context artifact"` (pinned by
`replay_classifier.py` lines 167–172).

### 3.2 Host re-validation failure under `semantic`

Condition: the validator's host-side re-validation of returned /
produced artifacts did not produce a `ValidationReceipt` admissible
at semantic closure.

Forced outcome: `semantic → degraded` (when the validator's policy
admits degraded with a named reason) or `semantic → unreplayable`
(when the re-validation failure is terminal). A
`DriftEventRecord` is emitted either way.

### 3.3 Audit pair incomplete under `diagnostic` or `semantic`

Condition: the enter/exit audit pair is durable but one of the
minimum-pair fields pinned by
`external_execution_admission_boundary/06 §5.3` is missing.

Forced outcome: the candidate is rejected at ingress (R-AUDIT-INCOH
at the boundary) **before** the classifier is invoked. If the host
policy admits the candidate at `unreplayable` per `03 §5` E-AUDIT-
UNRECOVERABLE, the classifier mints an `unreplayable` anchor
directly. Either way, no lesser-than-unreplayable class is
admissible.

---

## 4. Triggers that force `unreplayable` outright

### 4.1 Sealed revision absent

See §2.1. Forced outcome: `unreplayable` with
`unreplayable_reason = "sealed revision not found"`.

### 4.2 Audit pair durable-but-incomplete in the minimum list

See `external_execution_admission_boundary/06 §5.3` and `03 §5`
E-AUDIT-UNRECOVERABLE. Forced outcome: reject (no anchor) or
`unreplayable` (if host policy admits `unreplayable` over reject).

### 4.3 Ingress defer that no new evidence can close on this revision

Condition: ingress produced a `defer` that is not closeable within
this revision's evidence horizon (for example, a remote-worker
proof bundle that cannot be obtained under phase-1 rules).

Forced outcome: `unreplayable` with a named
`unreplayable_reason` citing the ingress defer class. The
remediation is a new revision, not an upgrade of this anchor (`00
§5`).

### 4.4 Caller explicitly requests `unreplayable`

See `replay_classifier.py` lines 190–196. Forced outcome:
`unreplayable` with `unreplayable_reason =
"caller-declared unreplayable"`. This is not a lowering trigger in
the automatic sense (the caller asked for it); it is listed here
for taxonomy completeness.

---

## 5. Triggers that are **not** lowering triggers

The following are signals that look like lowering triggers but are
not:

- **Caller requests `degraded`.** See `replay_classifier.py` lines
  182–188. This is a direct admission at the requested class, not
  a downgrade. The reason string `"caller-declared degraded"` is
  pinned.
- **Performance drift.** Slower replay does not lower class. Class
  is an evidence-shape statement, not a latency statement (`01 §4`).
- **Reviewer sentiment.** A human reviewer reading an artifact does
  not lower class. Class is authored by the classifier only (`00
  §6`).
- **Test failure elsewhere in the project.** Class is pinned to
  `(project_id, task_id, root_revision_id)`; a failure on an
  unrelated triple does not lower this anchor's class.

---

## 6. Ordering of trigger evaluation (classifier reference)

The classifier's phase-1 evaluation ordering is (from
`replay_classifier.py`):

1. Sealed revision presence check (§2.1 / §4.1).
2. Context / inference presence lookups.
3. Exact-class branch with INV-011 proof-bundle refusal
   (§2.5).
4. Semantic branch with context check (§3.1).
5. Diagnostic branch (self-honoring if requested).
6. Degraded branch (self-honoring if requested; §5 non-trigger).
7. Unreplayable branch (self-honoring if requested; §4.4).

This ordering is **not edited** by this taxonomy. It is cited here
so a reviewer can verify that the triggers above map 1:1 onto the
existing phase-1 code paths.

---

## 7. Invariants over trigger behavior

- Every lowering carries a named reason string.
- Every lowering attaches at least one `DriftEventRecord`
  (§23.19), except where the lowering is to `unreplayable` from
  sealed-revision-absent (which writes `unreplayable_reason`
  instead; a `DriftEventRecord` is not forced there by this
  taxonomy).
- Every lowering is host-authored.
- Every lowering follows a transition in `04 §2`.
- No lowering rewrites an existing anchor. An anchor is minted
  once; subsequent evidence produces a new anchor on a new
  revision (`06 §3`).

## 8. Net statement

These triggers are the exact conditions under which the five-class
taxonomy forces honesty. Each trigger has a pinned transition in
`04`, a pinned reason, and a pinned receipt-shape effect. Evaluation
is deterministic, ordered, and already implemented by the phase-1
classifier.
