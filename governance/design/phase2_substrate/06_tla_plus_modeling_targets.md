# 06 — Concurrency / State-Machine Surfaces Worth Future TLA+ Modeling

Scope: identify the concurrency and state-machine surfaces where TLA+
(or PlusCal) modeling would meaningfully strengthen Phase-2 hardening
*before* the relevant code is broadened. This is a **modeling
candidate list**, not a commitment to write specs in this increment.

Selection criteria (must satisfy at least three):
1. The surface has a known race window or interleaving hazard
   (already named in §22 contracts).
2. The surface has more than one independent state machine that
   communicates via shared state.
3. A bug here is silent or hard to test exhaustively (not a
   straightforward unit-test surface).
4. The constitution already mandates fail-closed semantics under
   ambiguity (so model checking has a clear correctness target).
5. The surface is in scope for Phase-2 hardening per §28's hardening
   order.

For each candidate: what to model, the property class to check, and
the evidence bar that would justify writing the spec.

---

## TLA-1. Atomic Approval Barrier (C22.3)

- **Why model:** concurrent contenders on the same task generation;
  revision-fence acquisition; "no seal between successful barrier
  verification and execution start"; deterministic one-winner rule
  with explicit losers fail-closed.
- **State machine boundaries:** approval entry → barrier check →
  fence acquisition → execution-start gate; concurrent seal
  attempts on overlapping roots.
- **Properties to check:**
  - Safety: at most one approval converts to execution authority for
    a given (root, task generation).
  - Safety: no execution starts after a fence-invalidating drift.
  - Liveness: under fairness, at least one valid contender either
    succeeds or all fail closed (no permanent stuck state on
    contention).
- **Why TLA+:** classic mutual-exclusion + drift-invalidation
  problem. Hard to cover by unit tests; trivial to model.
- **Evidence bar:** any observed flake in `AT-008` concurrency tests
  is sufficient to justify writing the spec; even without a flake,
  this surface is high-value because of constitutional priority.

## TLA-2. Capability Token Lifecycle (C22.6) — concurrent consume + revocation

- **Why model:** double-consume race, revocation-vs-consume race,
  crash-window ambiguity (`INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED`),
  cross-class escalation prevention, "revocation always wins"
  property.
- **Properties to check:**
  - Safety: at most one successful consume per single-use token.
  - Safety: a revoked token is never consumed successfully, even
    under concurrent issue/revoke/consume interleavings.
  - Safety: lower-class tokens never authorize higher-class effects.
  - Safety: post-crash recovery never resurrects a partially-consumed
    token to "available".
- **Evidence bar:** the existing AT-018 + AT-018 concurrent
  double-consume test pair already targets this; promoting to a TLA+
  spec is justified before any broader capability classes are
  admitted (§30.6 broadening rule).

## TLA-3. WAL Durability + Seal Transaction Ordering (C22.1, C22.2)

- **Why model:** the nine-step ordering routine in §22.2 has multiple
  crash windows, each of which must produce *deterministic*
  classification. Recovery interleaves with concurrent readers
  attempting to view "current truth".
- **Properties to check:**
  - Safety: no revision is visible as sealed before durability
    boundary is crossed.
  - Safety: every reachable crash window classifies to a single
    legal recovery outcome (no "maybe sealed").
  - Safety: dirty-tail truncation never erases a frame that
    participated in a legal sealed history.
  - Safety: mid-segment corruption halts automatic recovery.
- **Why TLA+:** crash-window state explosion is the canonical TLA+
  use case. Models also feed back into the Rust WAL classifier
  candidate (R-3 in `03`).
- **Evidence bar:** justified now, ahead of broader runner classes
  (§28 step 1 is already at the top of the hardening order).

## TLA-4. Quarantine Run Lifecycle (§9.7) under crash + reaper

- **Why model:** transitions across `prepared → entered → executing
  → exited_clean / exited_failed / exited_tainted →
  preserved_for_forensics → destroyed`, plus the startup reaper
  (proposed in `05`) running concurrently with new runs.
- **Properties to check:**
  - Safety: no run in `executing` is ever destroyed.
  - Safety: a run that should be preserved for forensics is never
    silently destroyed by the reaper.
  - Liveness: every terminal run reaches `destroyed` eventually
    under fairness and policy.
- **Evidence bar:** justified once substrate A or the
  phantom-workspace layer (`01`, `05`) is admitted, because both
  introduce stateful per-run resources and a reaper.

## TLA-5. Replay Class Adjudication (C22.5) — multi-source evidence

- **Why model:** `replay_classifier` combines truth-evidence
  completeness, context completeness, inference availability,
  environment fingerprint, nondeterminism tolerance class, and
  divergence reporting. Admissibility downgrades cascade.
- **Properties to check:**
  - Safety: no input combination yields a class above what evidence
    permits (no "exact" without all required inputs).
  - Safety: any missing dimension produces exactly one downgrade
    record with the dimension named.
  - Monotonicity: adding evidence cannot decrease class; removing
    evidence cannot increase class.
- **Evidence bar:** justified before any broadening of replay class
  policy or before substrate B/A "exact" claims are admitted (`04`).

## TLA-6. Taint Propagation Graph (C22.11, §9.9)

- **Why model:** `clean → suspected → tainted → quarantined →
  cleared_by_policy → archived` plus propagation across artifacts
  via causality refs. "No silent clearing" (`AT-028`) is a
  monotonicity property.
- **Properties to check:**
  - Safety: no transition violates the legal-transition table.
  - Safety: clearing a taint requires a governance event (no silent
    drop).
  - Safety: an artifact tainted via causality propagation is reachable
    from the originating taint source in audit.
- **Evidence bar:** justified before broader runner classes /
  validation lanes are admitted, because propagation surface area
  grows with substrate diversity (§01 substrates A/B/C).

## TLA-7. Worker Run Lifecycle (§9.6) ↔ Quarantine Run Lifecycle (§9.7) coupling

- **Why model:** worker and quarantine state machines run in lockstep
  but are independently restartable across crashes. The constitution
  forbids illegal `created → completed` direct transitions (`AT-023`)
  and similar shortcuts; modeling guards against future coupling
  bugs.
- **Properties to check:**
  - Safety: every worker terminal state is consistent with a quarantine
    terminal state.
  - Safety: `superseded` never leaves a forensics-required quarantine
    artifact in `destroyed` prematurely.
- **Evidence bar:** justified once worker concurrency increases
  beyond the Phase-1 single-lane tracer bullet.

---

## Out of scope for modeling now

- The `signoff_gate` evaluator: its complexity is in *which* gates
  exist, not in concurrent interleavings. Tests, not TLA+.
- Schema validation: pure functional surface; differential testing
  (R-2 in `03`) is the right tool, not TLA+.
- UI / shell ordering: explicitly out of scope.

## Discipline rules for any spec written in Phase-2

- Specs live under a future `governance/design/phase2_substrate/tla/`
  directory (not created in this increment).
- Each spec names the §22 contract and the AT/INV ids it bounds.
- Counterexamples found by TLC/Apalache become AT additions in
  `governance/implementation/`, not silent fixes.
- A spec is not authority; it is *evidence* under §3.4 and §31.
