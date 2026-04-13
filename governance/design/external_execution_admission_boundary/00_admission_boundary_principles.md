# 00 — Admission Boundary Principles

This file states the decision model that governs every clause of this
package. It introduces no constitutional rules; it is an application
of existing v11 sections to a single question:

> **What must be true at the seam between the Python authority surface
> and any future bounded external executor?**

## Constitutional anchors

- §3.1 Truth sovereignty — the kernel control plane is the single
  authority. No external executor may acquire any authority surface.
- §3.2 Default deny — at the boundary, *nothing* crosses unless
  explicitly admitted. Silence is not admission.
- §3.3 Replay honesty — substrate-introduced gaps in time, randomness,
  worker determinism, or audit binding force explicit downgrades and
  `DriftEventRecord` emission, never silent equivalence.
- §3.10 No new rules without physical evidence — this package adds no
  constitutional rules.
- §3.11 Authority locality — capability issuance, approval, sealing,
  and audit authoring live in the host; not in the guest, not in the
  sidecar, not in the broker shim.
- §3.12 Explicit downgrade discipline — the boundary's downgrade rules
  apply in both directions: it is as illegal to silently *raise* an
  executor's replay class as to silently *drop* it.
- §3.13 Minimality at the hot path — the boundary admits the smallest
  surface that suffices. Every additional capability granted to an
  executor must be justified per call, not per executor and not per
  substrate class.
- §3.14 Replacement-by-evidence — a future admission of any executor
  is governed by `phase2_promotion_gate`. This package adds a
  conformance dimension that gate must check; it does not weaken the
  per-candidate evidence bars.
- §27 Substrate strategy — mature first, internalize on evidence. The
  boundary is precisely the seam at which a not-yet-admitted substrate
  would have to behave correctly to even be evaluated for admission.
- §28 Hardening loop — the boundary is the surface against which
  hardening evidence accrues; it is not a hardening artifact itself.
- §29 Multi-vendor doctrine — workers are replaceable; authority
  remains singular. The boundary expresses this exactly: the host
  treats every external executor as a worker, not as a co-authority.
- §31 Sign-off honesty — admitting a boundary clause that has not been
  honored is not a sign-off; it is overclaiming.

## The boundary decision model

For any proposal that introduces or modifies an external executor
crossing this boundary, every clause in files `01`–`08` is evaluated
independently. A proposal is reviewed under exactly four legal
outcomes:

1. **Conforms.** Every applicable boundary clause is honored, and
   every authority surface listed in `01` remains in the Python
   control plane. The proposal *may* then be evaluated under
   `phase2_promotion_gate`. Boundary conformance is necessary, not
   sufficient.
2. **Defer-pending-conformance.** One or more boundary clauses are
   addressable but not yet addressed. The proposal is returned to
   design until they are.
3. **Reject.** A non-admission condition from `08` applies. The
   proposal is removed from consideration for this cycle.
4. **Demote.** A previously admitted executor is observed to have
   violated a boundary clause in production. The executor returns to
   `defer-pending-evidence` under `phase2_promotion_gate`'s demotion
   path, with the boundary violation as the new precondition.

There is no fifth outcome. In particular there is no "conforms with
caveats", no "informally conforms", no "conforms for a limited rollout".
Those map to `defer-pending-conformance` or `reject`.

## Default posture

**Default-deny at the boundary.** No call, byte, file handle, network
descriptor, capability handle, environment variable, clock read,
random read, or signal crosses the boundary unless an explicit
clause in this package admits it. The absence of a prohibition is
*not* an admission; the absence of an admission *is* a prohibition.

## Scope of the boundary

The boundary is **substrate-shape-agnostic**. A Wasmtime guest, an
Apple-VM Linux guest, a Linux/KVM sidecar, a remote worker, and an
APFS clonefile-backed phantom workspace all face the same boundary
clauses. Per-substrate evidence and per-substrate entry criteria
remain in `phase2_promotion_gate/02_…`.

This is deliberate: the eight authority responsibilities in `01` do
not become slightly transferrable because the executor has a Linux
kernel inside it, nor slightly more transferrable because the
executor is a `clonefile()`-backed working directory on the host's
own filesystem. Substrate proximity to the host does not weaken the
boundary; if anything it makes the boundary more important, since the
temptation to share state with a "nearby" executor is greatest exactly
where that sharing is most damaging.

## Per-call, not per-executor

Boundary admission is per call (per single execution, per single
capability consumption) and not per executor lifetime. An executor
that was admitted to do A is not, by virtue of being admitted, allowed
to do B. Each capability is single-use, scoped, and reaped on use or
on timeout per §22.6.

## What the boundary is

- A **decision record** for what may and may not cross the seam.
- A **reviewer tool** that a signer can use under §31 to ask "does
  this proposal conform to the boundary, regardless of whether its
  substrate gate is closed?"
- A **filter** between any future bounded executor and the eight-
  stage signable path.

## What the boundary is not

- It is **not** a per-substrate evidence bar. That belongs to
  `phase2_promotion_gate/02_…`.
- It is **not** a contract. It introduces no AT/INV identifiers.
- It is **not** a schema. It changes no receipt shapes.
- It is **not** a permission slip. Boundary conformance does not
  imply admission; admission still requires `phase2_promotion_gate`
  closure plus §31 sign-off.
- It is **not** retroactively applicable to existing modules. Phase-1
  runtime modules continue to operate under existing constitution
  and contracts; this package speaks only to the future seam at which
  external executors would attach.

## Honesty rules that apply to every clause in this package

1. **Named surface.** Every authority surface in `01` is named
   explicitly. An unnamed "miscellaneous authority" clause is not
   admissible and does not appear in this package.
2. **Named direction.** Every boundary clause specifies host→executor
   or executor→host (or both). A clause that is silent on direction is
   a defect in this package and must be repaired before admission.
3. **Single authority surface untouched.** No clause may move any of
   the eight authority responsibilities out of the Python control
   plane. A clause that does so is a defect.
4. **Downgrade path first.** Any executor whose outputs might not be
   "exact" cannot be admitted until `replay_classifier`'s downgrade
   path emits `DriftEventRecord` for the exact dimension that executor
   weakens. The downgrade path is a precondition to admission, not a
   follow-up.
5. **No aesthetic admissions.** Substrate elegance, language fashion,
   guest-OS familiarity, packaging convenience, or "feels cleaner"
   are not boundary-conformance arguments and are not admissible.
6. **No silent widening.** A boundary clause is not weakened by
   adjacent code, configuration defaults, environment variables, or
   release packaging. If a future change would weaken any clause, that
   change requires its own design increment.

## How this package is consumed

A reviewer or signer approaching any proposed external-executor
admission PR should:

1. Identify the executor and its substrate shape.
2. Walk every clause in files `01`–`06` and verify that the proposal
   honors each on the named direction.
3. Walk file `08` and verify that no non-admission condition applies.
4. Walk file `07` and verify that the matching `phase2_promotion_gate`
   per-candidate evidence is *also* present; boundary conformance is
   not a substitute.
5. Apply §31 sign-off on that combined basis.

Any step that cannot be completed honestly is a denial, by default.
