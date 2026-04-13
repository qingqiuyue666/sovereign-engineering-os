# 04 — Exact Downgrade Paths Between Claim Classes

Scope: the permitted directed transitions between the five classes.
A "downgrade" is the classifier arriving at a class **lower** (in the
`01 §3` ordering) than the caller requested, because the higher
class's evidence in `03` was not fully met.

Constitutional anchors: §3.12 (honest downgrade), §22.5, §23.19, §24.2
(INV-010, INV-011).

This file describes only the *graph*. The conditions that force the
transitions live in `05`. The forbidden transitions live in `07`.

---

## 1. Ordering (re-statement)

    exact  >  diagnostic  >  semantic  >  degraded  >  unreplayable

Strictly linear. Classes are totally ordered for the purpose of
downgrade traversal.

## 2. Permitted downgrade graph

Legend:
- A node is a claim class.
- A directed edge `A → B` means: "a caller-requested class `A` may
  result in a classifier-admitted class `B`, given the shortfall
  conditions named in `05`."
- Self-loops are omitted (every class trivially honors itself when
  its evidence is present).

```
     exact
       ├──► diagnostic
       ├──► semantic
       ├──► degraded
       └──► unreplayable

  diagnostic
       ├──► semantic            (permitted only when diagnostic
       │                         evidence is met but the requested
       │                         class was exact; see §4)
       ├──► degraded
       └──► unreplayable

   semantic
       ├──► degraded
       └──► unreplayable

   degraded
       └──► unreplayable

  unreplayable
       (terminal — no further downgrade)
```

That is the entire graph. Anything not listed above is forbidden by
`07 §7` (silent class raise) or `07 §9` (undeclared transition).

## 3. One-step and multi-step downgrades

### 3.1 One-step

A one-step downgrade is the classifier moving from the requested
class `A` to the immediately adjacent lower class `B`, where
`A > B` and no class strictly between `A` and `B` is admissible.

Examples (phase-1 classifier, current code):

- Request `exact`, `has_inference_artifact == False` → admit
  `degraded` (one-step in the sense that `diagnostic` /
  `semantic` are not re-adjudicated here; see `replay_classifier.py`
  lines 121–135). Note: phase-1 takes the `exact → degraded` jump
  directly; this is a *permitted* multi-skip transition (`§3.2`),
  not a violation.

### 3.2 Multi-step (skip-level) downgrades

The classifier **may** skip intermediate classes when the skipped
class is no more satisfiable than the final class given the current
evidence. For example:

- Request `exact` with `has_inference_artifact == False`.
  `diagnostic` may also require the inference artifact under the
  validator's policy; if both are unsatisfiable, the classifier
  emits `degraded` with a named reason directly. This is the
  **phase-1 behavior** and is explicitly permitted.

Skip-level downgrades are legal only when the skipped class's
evidence is *also* not met. A skip over a class whose evidence is
met is a silent hold and is forbidden (`07 §10`).

### 3.3 Downgrade to `unreplayable`

`unreplayable` is reachable from any of the four higher classes.
It is also reachable from a direct caller request. When reached by
downgrade, `unreplayable_reason` is populated from the terminal
shortfall named in `05 §4`. A `degradation_reason` **may** additionally
be present if the path went `A → degraded → unreplayable`; see
`03 §5`.

---

## 4. Diagnostic vs semantic on downgrade from exact

When `exact` is requested and fails its evidence closure, the
classifier admits at the highest of `{diagnostic, semantic,
degraded}` whose evidence is met:

- If E-CTX + E-INF + audit binding are all present but a binding
  dimension forced a downgrade (shim drift, worker-determinism
  shortfall, etc.), admit `diagnostic` or `semantic` depending on
  which class's full evidence is met.
- If E-CTX is present but E-INF is not, the phase-1 classifier
  admits `degraded` (see `replay_classifier.py` lines 121–135);
  this is the pinned phase-1 behavior.
- If E-CTX is absent under an `exact` or `semantic` request, the
  phase-1 classifier admits `degraded` with the
  `"missing context artifact"` reason (lines 167–172).

The classifier's phase-1 ordering is **not edited** by this design
package. This taxonomy only states what the ordering means and
what it must honor.

---

## 5. Downgrades that are *not* transitions

Some transitions look like downgrades but are not:

### 5.1 Caller-requested class already at or below evidence

If the caller asks for `degraded` and the classifier admits
`degraded` with `caller-declared degraded` as the reason (see
`replay_classifier.py` lines 182–188), this is not a downgrade; it
is a direct admission at the requested class. No `DriftEventRecord`
is forced by this taxonomy in that case (§23.19 may still be
triggered by other signals, but not by this taxonomy's downgrade
rule).

### 5.2 Caller-requested `unreplayable`

`unreplayable` requested is `unreplayable` admitted (see
`replay_classifier.py` lines 190–196). Not a downgrade.

---

## 6. Forbidden transitions (pin — full list in `07 §9`)

For the avoidance of doubt:

- `unreplayable → *` — forbidden. `unreplayable` is terminal for
  the revision.
- `degraded → semantic / diagnostic / exact` — forbidden. An
  existing `degraded` anchor may not be upgraded. New evidence
  produces a new anchor on a new revision.
- `B → A` where `B < A` (any upward transition) — forbidden (`07
  §7`).
- `A → A` by silent rewrite of `degradation_reason` — forbidden
  (an anchor is immutable after mint; see `06 §3`).

---

## 7. Evidence-shortfall graph (preview)

The graph in §2 answers "*which* transitions are legal." The
conditions that force *which specific* transition fires live in `05`.
A quick preview, by shortfall:

| Shortfall | Typical forced outcome |
|---|---|
| Sealed revision absent | `→ unreplayable` |
| Context artifact absent | `→ degraded` (for `exact` and `semantic` requests) |
| Inference artifact absent under `exact` | `→ degraded` (phase-1 rule) |
| Equivalence proof bundle asserted under `exact` | `→ degraded` (INV-011; phase-1 rule) |
| Audit pair incomplete (min list of `external_execution_admission_boundary/06 §5.3` missing) | `→ unreplayable` (or reject before ingress) |
| Time/random/worker binding short under `exact` | `→ diagnostic` or `→ semantic` or `→ degraded` per validator policy |
| Taint propagated to candidate material | `→ degraded` (or reject under R-TAINT if ingress refuses) |
| No evidence at all | `→ unreplayable` |

The full mapping, with the exact invocation conditions, lives in
`05`.

---

## 8. Invariants

- Every downgrade carries a named reason (§23.19 + §23.12).
- Every downgrade is host-authored (`06 §1`).
- Every downgrade traverses a transition listed in §2.
- No upgrade exists in the graph. An upgrade path would require a
  new anchor on a new revision with new evidence (no in-band
  promotion, `00 §5`).
- `unreplayable` is terminal for the revision (§3.3).

## 9. Net statement

The downgrade graph is tight, directed, acyclic, and terminates at
`unreplayable`. It is the single source of truth for permitted
transitions. The conditions that fire a specific edge are named in
`05`. The combinations that are forbidden regardless of graph
membership are named in `07`.
