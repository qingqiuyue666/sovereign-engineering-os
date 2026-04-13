# 08 — Unresolved Blockers vs Recorded Semantic Risks

Scope: separate the two categories honestly.

- A **blocker** is an item that, if not resolved, makes this design
  package incorrect or contradictory. A blocker prevents review-
  readiness.
- A **recorded risk** is an item the design acknowledges, names, and
  defers — a semantic tension the taxonomy does not resolve and does
  not pretend to resolve. Recorded risks do not block review; they
  set expectations for later governance increments.

Constitutional anchors: §3.10, §3.14, §27, §31.

---

## 1. Unresolved blockers

**None.**

The five-class set is already pinned in two frozen phase-1 surfaces
(the schema enum and the `ReplayClass` enum). The per-class evidence
items are already frozen fields on existing artifacts. The downgrade
graph is already honored by the phase-1 classifier. The forbidden-
claims rules are already implied by INV-010, INV-011, and §3.12 and
pinned by phase-1 code.

This package therefore does **not** introduce any unresolved blocker.
A future governance increment that wants to change the taxonomy
(add, rename, merge, split a class; relax INV-010 or INV-011) would
introduce its own blockers at that time; those are not in scope
here.

---

## 2. Recorded semantic risks

These are real tensions the taxonomy lives with. They are recorded
so a reviewer knows the package is not pretending to resolve them.

### 2.1 Class-label pressure when an external executor is present

The five labels were chosen before the external execution admission
boundary introduced four per-substrate class ceilings (`06 §7` of
that package). Under substrate C (sidecar / remote worker), the
default admissible ceiling is `semantic`; under substrate A and
clonefile helpers, higher classes are possible; substrate B (WASI)
can in principle reach `exact`. A reviewer reading a `semantic`
anchor produced by a substrate-C executor and a `semantic` anchor
produced by a host-internal workload sees the same class string
while the underlying posture differs.

Recorded stance: the class is an evidence-shape statement, not a
substrate identifier. The substrate identity lives in the audit
record (`environment_fingerprint`). The taxonomy does not encode
substrate shape.

### 2.2 `degraded` vs `diagnostic` overlap under partial evidence

There are evidence configurations where `degraded` and `diagnostic`
both look admissible (context present, binding short but auditable,
decision trace partially reconstructable). The phase-1 classifier
resolves the overlap deterministically (it admits `degraded` when
the request was `exact` and either context or inference is missing;
it admits `diagnostic` when the request was `diagnostic` and its
evidence is met).

Recorded stance: the classifier's ordering is pinned (`05 §6`). A
future governance increment may wish to introduce a more granular
rule; until then, the phase-1 ordering is the authority and the
taxonomy does not second-guess it.

### 2.3 `unreplayable` vs absent-anchor distinction in review UX

`unreplayable` is a minted anchor; "no anchor at all" is a different
state. A reviewer UX that renders both as "cannot replay" is not a
taxonomy violation (it is a UX rendering choice) but is a source of
confusion.

Recorded stance: `07 §6` forbids the taxonomy itself from conflating
the two. UX is out of scope for this package, so the rendering risk
is recorded rather than solved.

### 2.4 `semantic` class drift when validator policy changes

`semantic` depends on the validator's semantic contract. If a
validator's contract is later tightened or relaxed, anchors already
minted at `semantic` keep their class string while the *meaning* of
that string for that validator drifts.

Recorded stance: an anchor is bound to a `version_tuple_hash` which
captures the validator's version at mint time. A reviewer must
interpret `semantic` with reference to the version. The taxonomy
does not add a per-anchor "validator policy at mint" field; that
would be a schema change out of this package's scope.

### 2.5 Equivalence-proof-bundle posture under phase 2

INV-011 forbids uncertified equivalence from being `exact`. Phase 1
does not admit proof bundles at all. A future phase-2 increment may
admit signed, audited equivalence bundles that raise above
`semantic` for substrate-C outputs. That change is **not** made
here.

Recorded stance: if and when proof bundles are admitted, this
taxonomy will need to state (a) how a bundle augments evidence
without rewriting an anchor, and (b) whether a bundle licenses
`exact` or caps at `semantic`. That work is deferred.

### 2.6 `environment_fingerprint` field pressure under shim-policy
variants

`environment_fingerprint_hash` is a single string that the audit
binding populates from a composition of shim policies (time,
random, worker, audit). A reviewer asking "which dimension drifted"
must inspect `DriftEventRecord.dimension`, not the fingerprint.

Recorded stance: `DriftEventRecord` is the per-dimension story;
the fingerprint is the composite. The taxonomy does not decompose
the fingerprint.

### 2.7 Taint-propagated candidate with otherwise clean classifier
intent

When a `TaintRecord` propagates but every other evidence item for
`exact` would be met, the taxonomy requires the class to lower per
`05 §2.6`. Some callers may wish to see `exact + taint-noted`; this
shape does not exist in the taxonomy.

Recorded stance: taint is a shortfall dimension. `exact` is denied.
`degraded` with the taint reason named is the honest admission.

### 2.8 Audit-pair durable-but-incomplete treated as `unreplayable`

`03 §5` E-AUDIT-UNRECOVERABLE routes some durable-but-incomplete
audit pairs to `unreplayable` rather than reject. A reviewer may
find it easier to interpret "reject" as "no anchor" and
"unreplayable" as "anchor minted but unusable"; the taxonomy treats
the latter as a valid state and the former as the ingress-layer
outcome.

Recorded stance: the split between reject (no anchor) and
unreplayable (anchor, no replay) is intentional and is pinned by
the boundary package (`external_execution_admission_boundary/06 §5.3`)
and this taxonomy.

---

## 3. Residual-honesty statement

The residuals above are real and named. Each is either a
substrate-level tension (2.1, 2.5, 2.6), a policy-level tension
(2.2, 2.4), a UX-level tension (2.3, 2.8), or an input-level
tension (2.7). None of them invalidates the class set, the
per-class evidence, the downgrade graph, the auto-lowering
triggers, or the forbidden-claims rules. Each is a semantic risk
acknowledged openly so a reviewer can disagree with the residual
stance rather than being surprised by it later.

## 4. Net statement

**No unresolved blockers.** Eight named semantic risks. The
taxonomy does not pretend they do not exist; it pins its stance on
each and defers the ones that would require a constitutional or
schema change to a later governance increment.
