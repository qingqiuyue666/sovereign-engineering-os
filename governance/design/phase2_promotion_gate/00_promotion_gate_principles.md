# 00 — Promotion Gate Principles

This file states the decision model that governs every per-candidate
gate defined in this package. It introduces no constitutional rules;
it is an application of existing v11 sections to a specific question:
**when may a phase-2 design item become implementation work?**

## Constitutional anchors

- §3.1 Truth sovereignty — the kernel is the single authority.
- §3.3 Replay honesty — downgrades are explicit, never silent.
- §3.10 No new rules without physical evidence — this package adds
  none.
- §3.12 Explicit downgrade discipline — any substrate whose outputs
  fall short of "exact" must route through the classifier's downgrade
  path before admission.
- §3.13 Minimality at the hot path — fewer moving parts on the
  authority surface; substrate additions are justified, not assumed.
- §3.14 Replacement-by-evidence — nothing is replaced or adopted
  without a triggering measurement or failure.
- §27 Substrate strategy — mature first, internalize on evidence.
- §28 Hardening loop — the order in which Phase-2 hardening steps are
  addressed.
- §31 Sign-off honesty — no claim is admitted above what evidence
  supports.

## The promotion decision model

Every gate is a yes/no decision on a single candidate, answered by the
same question:

> Does the named evidence artifact exist, and does it satisfy the
> named threshold, and is the named reversibility path in place?

The decision model has four legal outcomes:

1. **Admit** — all entry criteria met; candidate passes to
   implementation under the §28 hardening loop.
2. **Defer-pending-evidence** — candidate is still a valid phase-2
   target but at least one named evidence artifact is missing; work
   remains in design.
3. **Reject** — a named non-admission condition (see
   `06_explicit_non_admission_conditions.md`) applies; candidate is
   removed from the phase-2 target list for this cycle.
4. **Demote** — candidate was previously admitted and a later failure
   invalidates the admission; candidate returns to design with the
   failure record as the new precondition.

There is no fifth option. In particular there is no "admit with
caveats", no "admit informally", no "admit for exploration", and no
"admit because the calendar is pressing". Those map to
`defer-pending-evidence` or `reject`.

## Default posture

**Default-deny.** A candidate is not admitted unless its gate has
been *explicitly* closed with the named evidence and an explicit
sign-off record. Silence is never admission. The absence of a
rejection is never admission.

## Scope of the gate

Per-candidate, not phase-wide. Admitting substrate B (Wasmtime/WASI)
does not admit substrate A. Admitting R-1 (`version_tuple` hash
kernel) does not admit R-2 (schema validator core). This is a direct
application of §3.14: evidence attaches to the specific replacement
being proposed.

## What the gate is

- A **decision record** that lists, per candidate, the concrete
  artifacts required for admission and the conditions that forbid it.
- A **reviewer tool** that a signer can use under §31 to ask
  "does this admission actually clear the bar?"
- A **filter** between `phase2_substrate/` (design map) and any
  future implementation branch.

## What the gate is not

- It is **not** a schedule. It has no calendar commitments.
- It is **not** a promise that every candidate will pass. Some
  candidates will likely never pass (substrate C default posture is
  rejection for most workloads).
- It is **not** a new contract. It imposes no runtime behavior and
  adds no AT/INV identifiers.
- It is **not** a substitute for §31 sign-off. A closed gate is
  *necessary*, not *sufficient*: sign-off still applies at the point
  of merge.
- It is **not** reviewable at the phase level. A reviewer who reads
  "phase-2 is admitted" should reject that claim and ask which
  specific candidates have their per-candidate gates closed.

## Honesty rules that apply to every gate in this package

1. **Named artifact.** Each entry criterion names the exact artifact
   that must exist (a measurement in the form "module X costs Y ms on
   corpus Z", a receipt class in audit, a TLA+ counterexample count,
   a reproducible failure record, etc.). An unnamed "sufficient
   evidence" clause is not a valid entry criterion and does not
   appear in this package.
2. **Pre-registered failure record.** Where the admission is hard to
   reverse, the candidate's gate names the kind of failure that
   would trigger demotion, so that demotion is not argued about
   after the fact.
3. **Single authority surface untouched.** No admission is allowed
   to move authority out of the Python control plane. If a candidate
   requires doing so, it is automatically rejected (see
   `06_explicit_non_admission_conditions.md`).
4. **Downgrade path first.** Any substrate whose outputs might not
   be "exact" for replay cannot be admitted until the classifier's
   downgrade path and the `DriftEventRecord` wiring are *already*
   proven to emit for the exact dimensions that substrate weakens.
   The downgrade path is a precondition, not a follow-up.
5. **No aesthetic admissions.** Language preference, framework
   preference, packaging preference, or "feels cleaner" are not
   entry criteria and will not appear as artifacts.

## How this package is consumed

A reviewer or signer approaching any proposed phase-2 implementation
PR should:

1. Identify which candidate(s) the PR promotes.
2. Open the matching section (02 / 03 / 05 / etc.).
3. Verify each named evidence artifact against linked reality.
4. Verify no non-admission condition from `06` applies.
5. Verify that Phase-wide prerequisites from `01` are met.
6. Apply §31 sign-off on that basis.

Any step that cannot be completed honestly is a denial, by default.
