# 08 — Explicit Non-Admission Conditions

Scope: the **conditions under which an external executor is forbidden
from being admitted, regardless of how attractive the proposal looks
or how many gate clauses it has otherwise closed**. This file is the
boundary-level analogue of `phase2_promotion_gate/06`; the two are
independent and both apply (file `07 §3`).

These are not informational warnings. They are denials.

Constitutional anchors: §3.1, §3.2, §3.10, §3.11, §3.12, §3.13,
§3.14, §27, §31.

---

## 8.1. Authority moves out of the Python control plane

**Denial trigger:** the proposed executor (or its broker, transport,
shim, or wrapper) holds, authors, mints, or adjudicates any of the
eight authority responsibilities A-1..A-8 listed in file `01 §1`.
This includes the `version_tuple` *composition policy*; the hash
kernel itself remains a separate downshift candidate governed by
`phase2_promotion_gate/03 R-1`.

**Why:** §3.1 truth sovereignty; §3.11 authority locality. Authority
in an executor is no longer the kernel.

**No exceptions.** "Performance", "ergonomics", "elegance",
"colocation with the data" are not grounds.

---

## 8.2. Broker boundary cannot be honored

**Denial trigger:** the proposed broker implementation cannot satisfy
all of BROK-1..BROK-7 (file `02 §7`). Concretely: it forwards
capability tokens to the executor, exposes non-opaque handles, allows
handle synthesis by the executor, fails to bracket issuance with a
WAL-durable record, fails to reap orphans into `exited_failed`/
`exited_tainted`, or cannot canonicalize the handle catalog for
`environment_fingerprint`.

**Why:** the broker is the only legal path for capability flow across
the boundary; a broker that does not honor its shape is the seam
collapsing.

**No exceptions** for "we'll fix it after the first ship".

---

## 8.3. Pre-admission checks cannot be honored per call

**Denial trigger:** the proposed implementation cannot honor every
pre-admission check Q-1..Q-8 (file `03 §1`) on every invocation.
Examples: a substrate that allows envelope construction without §22.4
guarantees, a transport that exposes effect handles before the enter
`AuditRecord` is durable, an executor that can be invoked by another
executor (chaining).

**Why:** the per-call admission discipline is what keeps the boundary
load-bearing in production.

**No exceptions** for "warm cache" or "fast path" admission shortcuts.

---

## 8.4. A forbidden surface from file `04` is reachable

**Denial trigger:** any of the file-`04` forbidden surfaces is
reachable, even conditionally:

- network egress that is not host-mediated (F-1);
- mutation outside the per-run ephemeral root and per-run write-once
  output area (F-2);
- mint or modification of authority artifacts (F-3);
- direct write to audit ledger or any receipt store (F-4);
- acquisition of host secrets (F-5);
- subprocess that escapes the boundary (F-6);
- capability re-issuance, forwarding, or aliasing (F-7);
- ambient nondeterminism (F-8);
- self-modification of executor image (F-9);
- effects on shared OS state (F-10);
- influence on host scheduler / budget / reaper (F-11);
- influence on `replay_classifier` (F-12);
- influence on taint graph attribution (F-13).

**Why:** these are the surfaces whose denial *is* the boundary. A
single reachable forbidden surface is the boundary breached.

**No exceptions** for "sometimes useful" or "behind a flag".

---

## 8.5. Class is silently raised on ingress

**Denial trigger:** the proposed ingress can promote a candidate to a
higher replay class than the four-dimension evidence (file `06`)
supports, without an explicit `DriftEventRecord` and without
`replay_classifier` adjudication. Equivalent: the proposed ingress
admits `exact` while any of time, randomness, worker determinism, or
audit binding is short of `exact` minimum.

**Why:** §3.12 downgrade discipline applies in both directions.
Silent class raises are as dishonest as silent class drops.
(`phase2_promotion_gate/06.4` denies this at the gate level; this
package denies it at the per-call level.)

---

## 8.6. Admission on aesthetic, roadmap, or convenience grounds

**Denial trigger:** the proposal's justification is, explicitly or
implicitly, one or more of:

- "the boundary is in the way";
- "the broker is too strict";
- "the per-call admission is slow";
- "the four-dimension binding is overkill for this workload";
- "we know this executor is deterministic";
- "other systems do it this way";
- "the roadmap suggests we'll need this";
- "the user experience improves if we relax X".

**Why:** §3.14 forbids ideological internalization; §27 forbids
substrate adoption without measurement; §3.13 forbids hot-path
weakening for convenience. This package does not relax for
ergonomics. (`phase2_promotion_gate/06.9` denies this at the gate
level; reaffirmed here per call.)

---

## 8.7. Admission PR bundles non-scope changes

**Denial trigger:** the admission PR includes changes to any of: UI,
dashboards, project shell, lane orchestration ergonomics, plugin
surfaces, extension API, marketplace, multi-vendor routing breadth,
benchmark breadth, fairness scheduler, distributed execution
runtime, cluster coordination, remote sync protocols, release /
packaging / notarization breadth.

**Why:** internalizing a substrate *and* expanding surface in one
step makes neither reviewable. Each is a separate increment.

**No exceptions.** (`phase2_promotion_gate/06.5` denies this at the
gate level; this package adds the boundary-level identical denial so
a PR cannot escape one by passing the other.)

---

## 8.8. Admission PR modifies the constitution or foundation

**Denial trigger:** the admission PR modifies
`governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
or `governance/implementation/v11_narrow_path_implementation_foundation.md`.

**Why:** §3.10. Authority-base changes land first, separately, and
both this package and `phase2_promotion_gate` are re-evaluated
against the new baseline.

---

## 8.9. Admission PR does not name the boundary-level demotion
trigger

**Denial trigger:** the admission PR does not name, in its
description, the specific kind of boundary violation (which clause
in files `01`–`06`) whose observation in production would demote
the executor back to `defer-pending-evidence` under
`phase2_promotion_gate`.

**Why:** §3.14 and the file-`00` principles. Boundary admissions
without a known reversal path are irreversible admissions, which
§27 forbids. (`phase2_promotion_gate/06.8` requires a per-candidate
demotion trigger; this clause adds the per-boundary one. They are
independent: a PR may have the gate trigger but not the boundary
trigger, and that is still a denial here.)

---

## 8.10. Admission PR changes receipt shape, schema, or contracts

**Denial trigger:** the admission PR modifies the shape of
`ReplayAnchor`, `ValidationReceipt`, `AuditRecord`,
`DriftEventRecord`, `CapabilityToken`, `ApprovalArtifact`,
`Revision`, `SnapshotRoot`, `TaintRecord`, `BudgetRecord`, or any
contract listed in §22.

**Why:** schema and contract changes are governance changes. They
land separately, before any executor admission depends on them. This
package's stance is identical to `phase2_promotion_gate/06.13` and
this package's hard non-scope rule (`README §"Hard non-scope"`).

---

## 8.11. Admission introduces a third role at the seam

**Denial trigger:** the proposal introduces a third party at the
seam beyond "Python control plane authority" and "bounded executor".
Examples: a "trusted shim that lives between the host and the
executor and sometimes mediates capability decisions", a "co-broker
that the executor can negotiate with", a "session manager that
issues handles independently of the broker", a "policy advisor that
reads classifier output and proposes class".

**Why:** the boundary admits exactly two roles (file `01 §7`). A
third role is authority diffusion; it cannot be reviewed under this
package because this package does not contemplate it.

**No exceptions** for "convenience layers" or "developer experience"
intermediaries.

---

## 8.12. Admission introduces multi-lane authority

**Denial trigger:** the proposal introduces multiple executors that
share authority state, distributed consensus on truth, or per-lane
authority. Equivalent to `phase2_promotion_gate/06.11`, repeated
here because lane-shape proposals are increasingly likely as
substrates appear.

**Why:** §3.1 kernel singularity; this is distributed execution
runtime and is hard non-scope (README).

**No exceptions** for "same-host multi-lane" either.

---

## 8.13. Admission relies on an untested broker crash-window

**Denial trigger:** the broker's WAL durability crash-window for
this executor's effect-handle table is not classified and tested
(file `02 §5.3`, `03 Q-7`). Specifically: the host cannot
demonstrate that, given a host crash mid-issuance, recovery reaps
outstanding handles into the correct exit class.

**Why:** §22.1 covers this for kernel WAL paths; the broker's
issuance path is on the same path by file `02 §5.3`. Untested
crash behavior at the broker is admitting on faith.

---

## 8.14. Admission claims `exact` for substrate C

**Denial trigger:** the proposal admits any Linux/KVM sidecar or
remote worker output at replay class `exact` automatically (i.e.,
without a signed, audited proof bundle and the four-dimension
evidence at `exact` minimum per file `06`).

**Why:** §5 baseline already declares cross-platform bit-identical
replay is not assumed; `phase2_substrate/04 §3` makes this explicit;
this package re-asserts it as a denial.

**Rule:** substrate C defaults to `semantic`. Higher requires the
proof bundle.

---

## 8.15. Admission allows executor-authored downgrade or
reclassification

**Denial trigger:** the proposed implementation lets the executor
emit, suppress, or influence its own `DriftEventRecord` or its own
classification. Includes: executor-side "I was deterministic" claims
that bypass classifier, executor-emitted shim policy strings that
the host accepts without re-derivation, executor-controlled
`environment_fingerprint` fields.

**Why:** classifier is host-only (file `01 §A-8`, `04 §F-12`).

---

## 8.16. Admission while the narrow path is unstable or in drift

**Denial trigger:** admission proposed while `main` has an open
narrow-path regression, a flaking AT on the tracer-bullet suite, or
an unresolved drift incident (`delta_register.yaml` open).

**Why:** §27 forbids internalizing substrates on a shaky base.
Stabilize first; admit later. (`phase2_promotion_gate/06.10` denies
this at the gate level; restated here so a per-call ingress
modification cannot slip in during instability either.)

---

## 8.17. Admission without a sign-off naming both gate and boundary

**Denial trigger:** the admission is merged without a §31 sign-off
record that names *both*: (a) the closed `phase2_promotion_gate`
candidate gate(s) with their named evidence, and (b) the boundary
clauses honored from this package.

**Why:** §31. A sign-off that does not say what it signs off on is
not a sign-off. A sign-off that names only the gate but not the
boundary is signing off on half the admission.

---

## 8.18. Admission via a "compatibility" or "shim" that hides the
seam

**Denial trigger:** the proposal introduces a compatibility layer
that "presents the executor as if it were the host" or a shim that
"pretends authority artifacts come from the host when in fact they
were authored elsewhere", including bridges that re-emit
`AuditRecord`s on behalf of the executor.

**Why:** the seam is supposed to be visible. A shim that makes it
invisible defeats the entire point of files `01`–`06`.

---

## 8.19. Admission predicated on disabling §22.11 taint propagation

**Denial trigger:** the proposal requests, configures, or implies
that §22.11 taint propagation is disabled for this executor's
inputs or outputs (e.g., "this validator is trusted, do not bind
taint to its outputs").

**Why:** §22.11 is a contract; the boundary does not get to opt out.
Trusted-validator hand-waving is denied.

---

## 8.20. Admission depends on a §22.4 weakening

**Denial trigger:** the proposal weakens any of the six §22.4
quarantine guarantees (network-off, host read-only, isolated caches,
disposable filesystem layer, bounded resources, secret isolation)
for the executor — at any layer (substrate, broker, transport,
shim, configuration, environment).

**Why:** §22.4 is the contract under which executors run. The
boundary does not weaken contracts; that is a separate, governed
increment.

---

## Summary posture

These conditions are not exhaustive edge cases. They are the
standard denials a reviewer should check before reaching the per-
candidate gates and the per-call boundary detail. An admission PR
that survives every one of §§8.1–8.20 has earned the right to be
evaluated against files `01`–`06` and against
`phase2_promotion_gate/02`–`05`; an admission PR that trips any one
of them is denied, regardless of how attractive the roadmap, the
calendar, or the engineering aesthetic makes it look.
