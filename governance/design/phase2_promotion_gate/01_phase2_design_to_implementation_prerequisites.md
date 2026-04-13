# 01 — Phase-2 Design → Implementation Prerequisites

Scope: the **phase-wide** prerequisites that must all hold before any
individual phase-2 substrate candidate becomes eligible for its own
per-candidate gate (02, 03, 05). These are the checks that apply
across the phase, once, before anything else.

A per-candidate gate may only be evaluated if every prerequisite on
this page is satisfied. A single failure on this page blocks the
entire phase — not one substrate, all of them.

Constitutional anchors: §3.10, §3.14, §27, §28, §30.3, §30.4, §31.

## PR-1. Narrow signable path is in steady state

The eight-stage signable path must be closed and steady. Specifically:

- `DELTA-FIRST-BUILD` and the narrow-path hardening increments already
  merged must be live in `main` with green CI.
- `AT-001`…`AT-030` (to the extent admitted in v11 narrow-path
  implementation foundation §18 and the merged hardening increments)
  must pass on the Phase-1 tracer-bullet corpus.
- No open "narrow-path regression" incident is recorded in
  `governance/implementation/delta_register.yaml` at the time of
  phase-2 prerequisite evaluation.

**Evidence artifact:** CI run identifier on `main` for the most recent
narrow-path regression suite, plus a hash of the delta register at
that commit.

**Why this is a prerequisite:** §27 forbids internalizing substrates
while the mature substrate is unstable. A shaky Phase-1 base
guarantees a shakier Phase-2.

## PR-2. Phase-2 substrate design package is frozen

The design package at `governance/design/phase2_substrate/` must be:

- merged to `main`,
- not edited in-flight during a phase-2 implementation PR (if a
  candidate reveals that the design is wrong, the design is updated
  in a *separate* design-only PR first, then the gate is re-evaluated
  against the updated design),
- referenced by the promotion gate package (this file and siblings)
  at a specific commit.

**Evidence artifact:** commit SHA of `phase2_substrate/` at the time
of each per-candidate gate evaluation, recorded in the PR description.

**Why this is a prerequisite:** §3.10 — the design must exist as
*physical evidence* before it is acted on. Simultaneous design and
implementation is the classic way to slide past a gate silently.

## PR-3. Replay downgrade path is already honest

Before any substrate (A, B, or C) can claim "exact" for replay, the
downgrade path from `replay_classifier` to `DriftEventRecord` must
*already* be in place and tested for every dimension the candidate
substrate would weaken. See `04_replay_determinism_audit_binding_evidence.md`
for exact dimension-by-dimension requirements.

**Evidence artifact:** a test in the existing acceptance suite (no
new AT id needed) that demonstrates a forced downgrade produces a
`DriftEventRecord` for each of: time, randomness, worker determinism,
audit binding.

**Why this is a prerequisite:** §3.3 and §3.12. A substrate that
introduces new nondeterminism *before* the downgrade path is proven
is an honesty regression.

## PR-4. Capability lifecycle is crash-honest without the substrate

C22.6 crash-window behavior (`INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED`)
must be demonstrably fail-closed **before** any substrate is added
that introduces a new capability consumption path (e.g., substrate A's
host-side broker). The existing AT-018 pair must be stable on `main`.

**Evidence artifact:** green `AT-018` and concurrent double-consume
AT-018 pair runs for the N most recent CI runs on `main`
(N defined in the PR that closes this gate, but not less than 10).

**Why this is a prerequisite:** §22.6. Adding a broker to a
fail-closed path is survivable; adding a broker to a fail-open path
silently broadens failure.

## PR-5. WAL recovery classification is stable

Before any candidate that touches WAL parsing or recovery semantics
(substrate B for determinism, substrate A's guest WAL handling policy,
Rust downshift R-3) is admitted, `AT-wal-recovery-*` / C22.1 crash
window classifications must be stable on `main`.

**Evidence artifact:** explicit list of every crash window class and
its current classifier decision, checked in unchanged for N
consecutive CI runs on `main`.

**Why this is a prerequisite:** §22.1. A moving WAL classification is
incompatible with a new parser implementation being admissible.

## PR-6. Evidence closure / ledger append throughput baselined

A baseline measurement of append-only ledger write cost and evidence
closure cost under Phase-1 tracer-bullet load must exist. This is
what Rust downshift candidates R-4 (ledger frame writer) and R-3 (WAL
classifier) measure against.

**Evidence artifact:** a recorded measurement file (form and
location are not pre-decided by this package — see
`07_unresolved_blockers_vs_recorded_risks.md`) showing baseline
cost per append and per closure on the current corpus, at a named
commit.

**Why this is a prerequisite:** §3.14 requires evidence of a
measured bottleneck before a replacement is admitted. Without a
baseline, "Rust would be faster" is aesthetic, not evidence.

## PR-7. Quarantine admissibility boundary is stated honestly

`kernel/validation/quarantine/` currently provides a *bounded
quarantine guarantee*, not a container-equivalent one. This fact
must remain explicit in documentation and receipts at the time of
any substrate A/B/C evaluation.

**Evidence artifact:** the quarantine admissibility statement (§22.4
in the constitution; `runner_adapter.py` module docstring; receipt
field semantics) is unchanged from the Phase-1 shipped wording at
the moment a substrate is being considered.

**Why this is a prerequisite:** §31 sign-off honesty. A substrate
that claims to "close" the bounded-quarantine gap can only be
evaluated against the explicit pre-existing gap. If the pre-existing
statement has been quietly upgraded, the evaluation is not honest.

## PR-8. No open non-scope drift

At the time of per-candidate gate evaluation, none of the items
listed under the README's non-scope block may be in-flight in the
same PR, in adjacent PRs, or as parallel work on the same branch.

Forbidden parallel items: UI work, dashboard work, plugin surfaces,
distributed execution, release breadth, multi-vendor routing
broadening.

**Evidence artifact:** a branch-diff check against the non-scope list
in README, included in the PR description.

**Why this is a prerequisite:** scope creep co-merged with a
substrate admission is one of the §27 failure modes (internalizing a
substrate *and* expanding surface in one step, so neither is
reviewable).

## PR-9. Sign-off honesty policy re-stated at admission time

The §31 sign-off for any substrate admission must explicitly state:

- which candidate is being admitted,
- which per-candidate gate (02 / 03 / 05) applies,
- which evidence artifact under that gate is claimed to be met,
- what the reversibility path is,
- what the pre-registered demotion trigger is.

**Evidence artifact:** the sign-off record itself, with these five
fields filled in before merge.

**Why this is a prerequisite:** §31. A sign-off that does not name
what it is signing off on is not a sign-off.

## PR-10. No silent edit of the constitution or implementation foundation

Between this package's commit and the admission commit, neither

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`, nor
- `governance/implementation/v11_narrow_path_implementation_foundation.md`

may be modified by a PR that also admits a substrate. If either is
legitimately updated, it is a separate PR, landed first, and the gate
is re-evaluated against the new baseline.

**Evidence artifact:** absence of changes to those two files in the
admission PR's diff.

**Why this is a prerequisite:** §3.10. Changes to the authority base
must be legible and separable from changes to the substrate.

---

## Summary

Ten phase-wide prerequisites. Every one of them must hold before any
per-candidate gate in this package may be evaluated positively. A
failure on any PR-n above is a **phase-wide** blocker, not a
candidate-specific one, and promotion is denied by default.
