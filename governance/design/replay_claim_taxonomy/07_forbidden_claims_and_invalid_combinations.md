# 07 — Forbidden Claims and Invalid Combinations

Scope: claim strings, receipt shapes, and class/transition
combinations that are **always denied**, regardless of how the
caller, validator, substrate, or external executor argues for them.

Constitutional anchors: §3.1 (truth sovereignty), §3.10 (no scope
creep / closed set), §3.12 (honest downgrade), §22.5, §23.12, §24.2
(INV-010, INV-011).

This file is the negative-space counterpart to `01`–`06`. A proposal
(runtime change, test, validator policy, substrate, executor, UI
surface) that exhibits any shape below is denied.

---

## 1. Invalid: `exact` with `degradation_reason` populated

An anchor at `replay_class_claim == "exact"` with a non-empty
`degradation_reason` is a contradiction. `exact` asserts that no
dimension fell short. A reason string names a shortfall. The two
cannot coexist.

Denial rule: reject the anchor shape. The classifier never mints
this shape in phase 1; a future change that emits it is a §3.1 /
§3.12 violation.

## 2. Invalid: `exact` with an active `DriftEventRecord` on a binding
   dimension

An anchor at `exact` with a present `DriftEventRecord` (§23.19) for
this `(task_id, root_revision_id)` naming any of the four binding
dimensions (time, randomness, worker determinism, audit binding) is
invalid. A drift event is a named shortfall; `exact` requires E-NO-
DRIFT (`03 §1`).

Denial rule: the classifier must lower to one of `diagnostic`,
`semantic`, `degraded`, or `unreplayable` per `04` / `05`.

## 3. Invalid: `unreplayable` with empty `unreplayable_reason`

An `unreplayable` anchor without a reason is a silent refusal. §3.12
requires honest naming of the reason.

Denial rule: reject the anchor shape. `unreplayable_reason` must
be populated (`03 §5`).

## 4. Invalid: `degraded` with no `degradation_reason` and no
   `DriftEventRecord`

A `degraded` anchor that names no dimension is an unlabelled
downgrade. §3.12 requires the named reason; `03 §4` requires both
the string and the drift event.

Denial rule: reject the anchor shape.

## 5. Invalid: overloading `replay_class_claim` for non-replay meaning

`replay_class_claim` is an evidence-shape statement about replay
fidelity. It is **not**:

- a validator-quality score,
- a confidence level,
- a priority / severity rank,
- a reviewer sentiment,
- a coverage metric,
- a cost / performance tier,
- a workflow-stage identifier.

A proposal that uses one of the five class names to encode any of
those meanings is denied. A surface that wants such a metric must
introduce its own field on its own receipt; it may not piggyback on
`replay_class_claim`.

## 6. Invalid: using `unreplayable` to mean "no anchor"

`unreplayable` is a class that is **present** on a minted anchor; it
does not mean the anchor does not exist. "No anchor" is a distinct
state owned by the signable-path orchestrator, not by this taxonomy.

Denial rule: a surface that reports "unreplayable" to mean "anchor
absent" is conflating two states. This package reserves
`unreplayable` for minted anchors only.

## 7. Invalid: silent class raise

Writing a class into an anchor that is strictly higher than the
class the classifier would have produced given the evidence present
is a silent class raise. INV-010 forbids it.

Denial rule: reject. The classifier is the sole authority; no
component may overwrite its decision upward.

## 8. Invalid: `exact` with `equivalence_proof_bundle_admitted ==
   True`

INV-011 forbids uncertified equivalence from being `exact`. Phase 1
does not admit equivalence-proof bundles at all; even a bundle the
caller claims is valid does not license `exact`.

Denial rule: the classifier must lower to `degraded` with
`degradation_reason = "equivalence proof bundle not admissible in phase 1"`
(pinned by `replay_classifier.py` lines 140–148).

## 9. Invalid: transitions outside the `04 §2` graph

Transitions not declared in `04 §2` — notably any upward transition
or any transition out of `unreplayable` — are forbidden.

Denial rule: reject. The graph in `04 §2` is closed.

Specifically forbidden:

- `unreplayable → degraded / semantic / diagnostic / exact` —
  `unreplayable` is terminal for the revision.
- `degraded → semantic / diagnostic / exact` — no upgrade on the
  same revision.
- `semantic → diagnostic / exact` — same.
- `diagnostic → exact` — same.

## 10. Invalid: skip over a class whose evidence is met

Skip-level downgrades (`04 §3.2`) are permitted only when every
skipped class's evidence is *also* unmet. Skipping a class whose
evidence **is** met is a silent hold and is forbidden.

Denial rule: reject. The classifier must admit the highest class
whose evidence is fully met.

## 11. Invalid: sixth class, rename, or merge

Introducing any of the following is a constitutional change, not a
design edit, and is denied at the package level:

- a sixth class (e.g., `provisional`, `attested`, `partial`,
  `tentative`, `best_effort`);
- a rename of any of the five (e.g., `exact` → `bit_exact`,
  `semantic` → `equivalent`);
- a merge (e.g., treat `degraded` and `diagnostic` as one);
- a split (e.g., `semantic_regressed` vs `semantic_equivalent`).

Denial rule: reject. Route via the master plan (§3.10), not this
design increment.

## 12. Invalid: executor-authored class

An external executor that writes `replay_class_claim` (directly, by
proxy, or by policy that the host honors without adjudication) is
forbidden per `external_execution_admission_boundary/04 F-3` and is
re-forbidden here for taxonomy completeness.

Denial rule: reject the anchor. The host classifier re-adjudicates.

## 13. Invalid: in-band promotion of an existing anchor

Editing an already-minted anchor's `replay_class_claim` to a higher
class is forbidden (§3.1, `00 §5`, `06 §2.4`). An anchor is
immutable after mint. New evidence produces a new anchor on a new
revision.

Denial rule: reject any write that alters an existing anchor's
class string.

## 14. Invalid: caller-declared class above the evidence

A caller request is an input, not an authority. A caller requesting
`exact` does not admit `exact` unless the E-* checklist for `exact`
is met. The classifier lowers per `05`.

Denial rule: the classifier's decision stands. Caller-requested
class has no authority to override evidence.

## 15. Invalid: writing a class to a surface other than a
   `ReplayAnchor`

`replay_class_claim` is a `ReplayAnchor` field. A surface that
writes one of the five class strings to a receipt that is **not** a
`ReplayAnchor` (for example, a `ValidationReceipt`, a `BuildReceipt`,
an `AuditRecord`, a `DriftEventRecord`, a UI string) is conflating
the taxonomy with other semantics.

Denial rule: the class belongs on `ReplayAnchor`. Where a surface
wants to *reference* a class, it references the anchor by id; it
does not re-author the string on its own receipt.

## 16. Invalid: reason strings outside the pinned set

Phase-1 pinned reason strings (from `replay_classifier.py`):

- `"sealed revision not found"` — §5 unreplayable reason.
- `"missing context or inference artifact; exact replay refused"` —
  exact-downgrade reason under missing context or inference.
- `"equivalence proof bundle not admitted in phase 1; downgrade required (INV-011)"` —
  exact-downgrade reason under proof-bundle assertion with other
  evidence also short.
- `"equivalence proof bundle not admissible in phase 1"` —
  exact-downgrade reason under proof-bundle assertion when other
  evidence is met.
- `"missing context artifact"` — semantic-downgrade reason.
- `"caller-declared degraded"` — caller-declared admission reason.
- `"caller-declared unreplayable"` — caller-declared unreplayable
  reason.

New reason strings are not introduced by this package. A future
runtime increment that needs a new string must route through a
governance change that names the new string and the trigger it
corresponds to.

Denial rule (for now): a reason string not in the pinned set, on a
phase-1 anchor, is a silent change and is denied.

## 17. Invalid combinations at a glance

| Class          | `degradation_reason` | `unreplayable_reason` | DriftEventRecord present? | Verdict |
|----------------|----------------------|-----------------------|---------------------------|---------|
| `exact`        | empty                 | empty                 | none on binding dim       | **valid** |
| `exact`        | non-empty             | any                   | any                       | **invalid** (§1) |
| `exact`        | empty                 | any                   | present on binding dim    | **invalid** (§2) |
| `diagnostic`   | empty or populated    | empty                 | may exist                 | **valid** |
| `semantic`     | empty or populated    | empty                 | may exist                 | **valid** |
| `degraded`     | non-empty             | empty                 | ≥ 1 present               | **valid** |
| `degraded`     | empty                 | empty                 | none                      | **invalid** (§4) |
| `unreplayable` | empty or populated    | non-empty             | may exist                 | **valid** |
| `unreplayable` | any                   | empty                 | any                       | **invalid** (§3) |

## 18. Net statement

The taxonomy denies silent raises, silent holds, unlabelled
downgrades, unreplayable-without-reason, exact-with-drift, sixth
classes, renames, merges, splits, executor-authored classes, in-band
promotions, and out-of-taxonomy reason strings. The surface area
for dishonesty is closed by construction.
