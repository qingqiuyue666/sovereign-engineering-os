# 09 — Unresolved Blockers vs Recorded Risks

This file separates *true* blockers (items that would prevent the
boundary specification from being honest at the design level) from
*recorded risks* (legitimate engineering unknowns about how a future
implementation would honor the boundary, which the design package
documents rather than resolves).

The classification rule is the same as in
`phase2_substrate/07` and `phase2_promotion_gate/07`: a blocker is a
constitutional ambiguity, a missing baseline artifact, or a
contradiction between the constitution and the Phase-1 foundation
that prevents writing this design honestly. Anything else is a
recorded risk that lives in this file and is routed to the right
later increment.

Constitutional anchors: §3.10, §3.14, §27, §31.

---

## True blockers

**None.**

Every dimension required to write this boundary specification was
satisfiable from:

- the existing constitution (§3.1, §3.2, §3.3, §3.10, §3.11, §3.12,
  §3.13, §3.14, §5.5, §22.1, §22.2, §22.3, §22.4, §22.5, §22.6,
  §22.10, §22.11, §22.13, §23.1, §23.3, §23.7, §23.11, §23.12,
  §23.13, §23.14, §23.17, §23.19, §27, §28, §29, §31);
- the existing Phase-1 implementation foundation (`v11_narrow_path_implementation_foundation.md`);
- the prior design packages `phase2_substrate/` (substrate map) and
  `phase2_promotion_gate/` (per-candidate evidence bar).

No constitutional ambiguity, no missing baseline artifact, and no
constitution-to-foundation contradiction prevented writing files
`01`–`08`. The boundary is fully expressible in terms of existing
v11 sections and existing schema fields used per file `06 §8`.

---

## Recorded risks (documented; not blocking the design)

### Risk RR-1. Host-side broker wire format under crash window

A future broker implementation must satisfy BROK-1..BROK-7 (file
`02 §7`) and the §22.1 WAL durability discipline for issuance (file
`02 §5.3`). The exact wire format is open (also recorded as
`phase2_substrate/07 Q-4`).

- Disposition: pinned at boundary-shape level in file `02 §2.3`
  (W-1..W-5). Concrete wire format is an implementation question for
  a later increment.
- Resolution path: closed when the broker is implemented under
  `phase2_promotion_gate/02 A-ENTRY-3` and TLA-2 (per
  `phase2_promotion_gate/05`), with §22.1 crash-window classification
  per `phase2_promotion_gate/02 CF-?`-class evidence.
- Not a design blocker: the boundary specifies what the wire must
  guarantee, not how to implement it.

### Risk RR-2. Reaper correctness for orphaned effect handles

The reaper (file `02 §5`) must be correct under host crash, executor
crash, sidecar transport silence, and clonefile-helper crash. The
exact reaper algorithm is open at implementation level.

- Disposition: pinned as required behavior R-1..R-4 in file `02
  §5.2` and as an admission-stage requirement (file `08.13`).
- Resolution path: design + implementation increment paired with the
  broker implementation; covered by `phase2_promotion_gate/02 CF-4`
  test coverage.
- Not a design blocker.

### Risk RR-3. Candidate byte-buffer size governance under §5.4

OUT-2 (per-run candidate byte buffer, file `04 §2`) and the
ephemeral output area (OUT-1) consume disk under §5.4 disk
governance. Per-call cap policy is design-only here and not yet
quantified.

- Disposition: file `04` requires bounded surfaces; quantifying
  bounds is a budget-governance question, separate from this
  package.
- Resolution path: handled in a budget-governance increment along
  with the broker implementation.
- Not a design blocker.

### Risk RR-4. Clonefile divergence attribution for phantom workspaces

APFS clonefile-backed phantom workspaces are bounded executors
under this package, but per-block divergence attribution back to a
specific run is open (also recorded as `phase2_substrate/07 Q-6`).

- Disposition: the boundary treats clonefile helpers identically to
  other executors (file `01 §5`); divergence accounting is a §5.4
  concern.
- Resolution path: empirical sampling during Phase-2 hardening (per
  `phase2_substrate/07 Q-6`), tracked separately.
- Not a design blocker.

### Risk RR-5. Canonical `environment_fingerprint` field uses for executor identity

This package requires that executor identity, version, base-image/
engine hash, shim policies, and handle catalog digest be bound into
`environment_fingerprint` (file `06 §8`). The exact *field uses*
within the existing `environment_fingerprint` shape are not pinned
here; this package explicitly does not change `ReplayAnchor` shape
(non-scope, README; `08.10`).

- Disposition: file `06 §8` enumerates the bindings required as
  *uses* of existing fields. The granular field mapping is an
  implementation-design question.
- Resolution path: addressed in the implementation increment that
  introduces the first executor under `phase2_promotion_gate`. If a
  field addition turns out to be necessary, that is a separate
  governance increment per `08.10` and `phase2_promotion_gate/06.13`,
  landed first.
- Not a design blocker (the boundary works with the current shape;
  the worst case is downgrade D-AUDIT for missing optional bindings,
  not boundary failure).

### Risk RR-6. Replay-class label pressure when an executor is present

Introducing an external executor will, by §3.12 and file `06 §7`,
produce more `diagnostic`/`semantic`/`degraded` admissions than the
status quo. Operationally this looks like "the system is downgrading
more"; politically this could create pressure to weaken the
classifier or the boundary.

- Disposition: file `08.5`, `08.6`, and `08.15` deny that pressure
  directly. The classifier is host-only and never relaxed for
  ergonomic reasons.
- Resolution path: organizational, not technical. Honest downgrades
  are correct outcomes.
- Not a design blocker.

### Risk RR-7. Sidecar partition silence classified as `exited_failed`

Substrate C transport silence is classified `exited_failed` (file
`03.6.2`) by default, and `exited_tainted` if there is reason to
suspect authority-side influence (file `03.6.3`). Operationally,
network blips will produce `exited_failed`s.

- Disposition: file `03 §6.2` is intentional and consistent with
  `phase2_substrate/01 §C` ("the host must treat sidecar silence as
  `exited_failed`, not `exited_clean`").
- Resolution path: per-substrate retry policy is a §29 routing
  question, not a boundary question; routing does not relax
  classification.
- Not a design blocker.

### Risk RR-8. Apple Silicon micro-architectural variance residual

Even a perfect substrate A admission cannot guarantee bit-identical
floating-point across two M-series machines of different generations
(`phase2_substrate/07 Q-1`; `phase2_substrate/04 §3`).

- Disposition: file `06 §4.1` already records this; `exact` is
  available only for integer/byte-deterministic workloads in such
  cases.
- Resolution path: empirical measurement during Phase-2 hardening
  per `phase2_substrate/07 Q-1`.
- Not a design blocker.

### Risk RR-9. WASI preopens minimization review burden

File `04 §1`'s IN-1 preopens, and file `02 §6.1`'s WASI mapping,
require a curated, minimal preopen set per executor session.
Maintaining this minimum across many validator sessions is review-
burden, not design-burden.

- Disposition: §3.13 minimality applies; per-call admission Q-3
  envelope review (file `03`) covers it.
- Resolution path: tooling for preopen-set audit is an
  implementation-time concern.
- Not a design blocker.

### Risk RR-10. Taint graph attribution for executor-returned bytes

§22.11 taint graph attribution to bytes coming back through OUT-1/
OUT-2 must propagate from the inputs (IN-1, IN-4) and from any
detected undisclosed taint (file `05 G-5`). The exact propagation
algorithm is a §22.11 implementation question.

- Disposition: file `05 G-5` requires intake; file `08.19` denies
  any disabling of taint propagation.
- Resolution path: covered by the §22.11 contract implementation;
  this package does not modify it.
- Not a design blocker.

---

## Why none of the above blocks the design

A design blocker for this package would be any of:

- a constitutional ambiguity that prevents drawing the
  authority/non-authority line (file `01`);
- a missing schema field that prevents host-side audit binding (file
  `06`) without a new contract;
- a contradiction between the constitution and the Phase-1
  foundation about who owns capability issuance, replay class
  adjudication, or audit authoring;
- a missing prior design package that this package depends on
  (`phase2_substrate/` and `phase2_promotion_gate/` both exist).

None of RR-1..RR-10 is one of these. Each is a properly named,
properly scoped, properly routed engineering question about how a
future implementation would honor the boundary, with the boundary
behavior itself fully specified at the design level. That is exactly
what a design package is supposed to do under §27 and §3.14.

---

## Honest residuals statement

- This package does not pretend the recorded risks are resolved.
- This package does not pretend that any external executor is
  authorized.
- This package does not pretend that boundary conformance alone is
  sufficient for admission; `phase2_promotion_gate` per-candidate
  evidence and §31 sign-off still apply on top (file `07`).
- This package is review-ready as an **external execution admission
  boundary design**, and is honestly **not** review-ready as
  authorization for any implementation work. Promotion of any
  executor from candidate to admitted is governed by
  `phase2_promotion_gate`, and conformance to *this* boundary is an
  independently necessary condition, per file `07 §3`.
