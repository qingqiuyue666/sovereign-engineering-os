# 07 — Dependency Relationship to `phase2_promotion_gate`

Scope: the **exact** relationship between this package and
`governance/design/phase2_promotion_gate/`. The two packages are
complementary, not redundant, not conflicting, and not interchangeable.
This file pins what each owns, what each defers to the other, and what
the order of evaluation is.

Constitutional anchors: §3.10, §3.14, §27, §28, §31.

---

## 1. The two packages compose, not compete

`phase2_promotion_gate/` is the **per-candidate evidence bar** that
must be closed before any phase-2 substrate (or Rust downshift, or
TLA+ spec, or clonefile workspace) is admitted to implementation. It
asks: *for this specific candidate, is the named evidence in place?*

This package — `external_execution_admission_boundary/` — is the
**substrate-shape-agnostic boundary** that any admitted external
executor must conform to, per call, regardless of which substrate
shape it instantiates. It asks: *at the seam between authority and
this executor, is the boundary honored?*

Both questions must be answered "yes" before any external executor
runs in production. Either "no" is a denial. The questions are
independent: a substrate that passes its per-candidate gate may still
fail this package's boundary, and vice versa.

---

## 2. What each package owns

### Owned by `phase2_promotion_gate/`

- The **per-candidate** evidence requirements for substrates A, B,
  and C (`02_execution_substrate_entry_criteria.md`).
- The per-candidate evidence requirements for Rust downshift items
  R-1..R-6 (`03_rust_downshift_entry_criteria.md`).
- The **phase-wide** prerequisites for any phase-2 implementation
  work (`01_phase2_design_to_implementation_prerequisites.md`).
- The TLA+ admission targets and their preconditions
  (`05_tla_plus_admission_targets_and_preconditions.md`).
- The phase-wide replay/determinism/audit-binding evidence bar
  (`04_replay_determinism_audit_binding_evidence.md`).
- The **promotion** decision model (admit / defer / reject / demote)
  for whether a candidate may leave the design shelf at all.
- A separate set of **non-admission conditions** at the gate level
  (`06_explicit_non_admission_conditions.md`).
- The **reversibility** policy per admitted candidate.

### Owned by this package (`external_execution_admission_boundary/`)

- The **authority-vs-non-authority split** (file `01`): which
  responsibilities never leave the Python control plane.
- The **broker boundary** (file `02`): what crosses host↔executor and
  in what shape.
- The **per-call execution admission rules** (file `03`): pre-
  admission checks, refusal classes, exit-class adjudication.
- The **allowed I/O surfaces and forbidden mutation surfaces** (file
  `04`).
- The **result-ingress rules** (file `05`): candidate-vs-admitted-
  truth, reject/downgrade/defer.
- The **per-invocation** audit-binding and replay minimum (file
  `06`).
- A separate set of **non-admission conditions** at the boundary
  level (file `08`), distinct from the gate-level set in
  `phase2_promotion_gate/06`.

---

## 3. Order of evaluation

A future admission PR that proposes to introduce or use an external
executor in production is evaluated in the following order. A failure
at any stage is a denial; later stages do not run.

### Stage 1 — Promotion-gate evaluation (per-candidate)

`phase2_promotion_gate/` is evaluated end-to-end for the candidate
substrate (A / B / C) and any Rust downshift item the PR proposes.
Specifically:

- phase-wide prerequisites (gate `01`) hold;
- the candidate's per-substrate gate (gate `02` for A/B/C; gate `03`
  for R-*) is closed with the named evidence;
- the replay/determinism/audit-binding evidence (gate `04`) is in
  place at the *substrate* level;
- relevant TLA+ admission targets (gate `05`) are met;
- no gate-level non-admission condition (gate `06`) applies;
- the candidate's blockers are blockers in the gate sense (gate
  `07`).

If any gate-stage check fails, the PR is denied at this stage. This
package is *not* consulted further for that candidate.

### Stage 2 — Boundary-conformance evaluation (per-call shape)

If Stage 1 passes, *this* package is evaluated:

- the proposed executor implementation honors the authority-vs-non-
  authority split (file `01`);
- the proposed broker honors BROK-1..BROK-7 (file `02 §7`);
- the proposed per-call admission honors Q-1..Q-8 (file `03 §1`);
- the proposed I/O surfaces are subset of the allowed surfaces (file
  `04`);
- the proposed ingress honors G-1..G-9 and the reject/downgrade/defer
  matrix (file `05`);
- the proposed audit/replay binding meets the per-invocation minimum
  for every dimension the executor weakens (file `06`);
- no boundary-level non-admission condition (file `08`) applies.

If any Stage 2 check fails, the PR is denied. The promotion gate
having already closed for this candidate is irrelevant; boundary
conformance is independently necessary.

### Stage 3 — §31 sign-off

If Stage 1 and Stage 2 pass, the §31 sign-off applies, with a record
that names both: the closed promotion-gate clauses *and* the boundary
clauses honored. A sign-off that does not name both is not a
sign-off (file `00 honesty rule 1`; consistent with
`phase2_promotion_gate/06.15`).

There is no fourth stage. There is no "informally apply Stage 2".
There is no "Stage 1 was thorough, so Stage 2 is implicit".

---

## 4. What overrides what

When the two packages appear to conflict (in practice they should
not, by design — the boundary is more specific where the gate is
more general), the following precedence applies:

1. **Constitution wins.** Both packages are applications of v11; if
   either appears to contradict v11, the constitution wins by
   construction (§3.10).
2. **Boundary wins on per-call shape.** A boundary clause about per-
   invocation behavior is the binding rule per call, even if the
   gate is silent. (Example: file `04 F-1` denies any non-mediated
   network egress; the gate does not need to repeat this.)
3. **Gate wins on per-candidate evidence.** A gate clause about
   per-candidate evidence is the binding rule for whether the
   candidate is even eligible, even if the boundary is silent.
   (Example: `phase2_promotion_gate/02 A-ENTRY-1`'s identified-
   workload requirement is a precondition the boundary does not
   re-impose.)
4. **More restrictive wins.** Where both speak to the same
   dimension, the more restrictive clause is applied. Neither
   package is allowed to weaken a constitutional rule in favor of a
   "smoother" outcome.

There is no mode in which the boundary excuses a gate clause, and
there is no mode in which a gate excuses a boundary clause.

---

## 5. Specific cross-references (informational)

The following cross-references are provided so a reviewer can
walk both packages side-by-side without ambiguity. None of these
introduce new requirements; they map equivalent or paired
requirements across the two packages.

| Concern | `phase2_promotion_gate/` | `external_execution_admission_boundary/` |
|---|---|---|
| Authority surfaces never moved | `06.1` (denial trigger) | `01 §1` (eight responsibilities) |
| Local-path saturation before substrate C | `06.2` | `08.4` (network-off forbidden) + `04 F-1` |
| `exact` claim without four-dimension evidence | `06.3` | `06 §7.1` + `08.5` |
| Silent class raise | `06.4` | `05 §I-2` + `08.5` |
| Bundled non-scope changes | `06.5` | `08.7` |
| Constitution / foundation modified by admission PR | `06.6` | `08.8` |
| Premature Python-reference removal | `06.7` | (out of scope here; remains a gate concern) |
| Demotion trigger missing | `06.8` | `08.9` (boundary-level demotion) |
| Aesthetic / roadmap-anticipation grounds | `06.9` | `08.6` |
| Admission while narrow-path unstable | `06.10` | (gate concern only) |
| Authority into a lane | `06.11` | `08.1` |
| Substrate enter/exit not test-covered | `06.12` | `03 §6` (host-side classification) |
| Receipt-shape change bundled | `06.13` | `08.10` |
| Broaden mutation classes bundled | `06.14` | `08.7` |
| Sign-off without naming candidate, gate, evidence, reversibility, demotion trigger | `06.15` | (consumed at stage 3) |
| Per-substrate evidence bar (CF-1..CF-7, A-/B-/C-ENTRY-*) | `02` | (boundary defers to gate) |
| Per-call broker shape (BROK-1..BROK-7) | (gate defers to boundary) | `02 §7` |
| Per-invocation audit-binding minimum | (gate defers to boundary) | `06 §5` |

---

## 6. What this dependency is *not*

- It is **not** a re-implementation. The boundary does not re-state
  per-candidate gates, and the gate does not re-state per-call
  boundary clauses.
- It is **not** an opportunity to relax either package by playing
  them against each other. Both apply.
- It is **not** an excuse to introduce a new package. If a future
  question arises that neither owns (e.g., release-time packaging of
  base images, per `phase2_substrate/07 Q-3`), it goes to a new
  design package, not into either of the existing two.
- It is **not** a schedule. Neither package commits to when any
  candidate will be admitted; both commit only to *what must be true*
  for admission.

---

## 7. Net statement

`phase2_promotion_gate/` is the visa counter; this package is the
customs inspection at the gate. A traveler who clears the visa
counter still has to clear customs; a traveler who clears customs
still needs the visa. Both checks are independent and both must
pass before any external executor runs in production. §31 sign-off
takes the combined record and decides.
