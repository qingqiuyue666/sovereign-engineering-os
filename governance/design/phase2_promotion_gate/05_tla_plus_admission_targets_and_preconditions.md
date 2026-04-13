# 05 — TLA+ Admission Targets and Preconditions

Scope: which TLA+ (or PlusCal) specs must be written, when they become
admission *preconditions* for which substrate work, and what counts as
closure. This is **design-only**; no TLA+ spec is written in this
increment.

This file translates
`governance/design/phase2_substrate/06_tla_plus_modeling_targets.md`
(candidate list) into a concrete admission-time precondition list.

Constitutional anchors: §3.4 (models as evidence, not authority),
§22.1, §22.2, §22.3, §22.5, §22.6, §22.11, §9.6, §9.7, §31.

---

## What "admission target" means here

A TLA+ spec is an *admission precondition* for a substrate or Rust
candidate when:

1. The candidate's implementation would change behavior in the
   surface that the spec models, **and**
2. Model-checking the spec yields counterexamples whose enumeration
   must be resolved (either by fixing the design or by explicit,
   justified exclusion) **before** the candidate is admitted.

TLA+ is not authority. A clean model-check is *evidence*, not a
guarantee; the audit ledger and tests remain the authority path per
§31. But an admission lacking a required spec where §28 or §30.6
broadening is implicated is denied.

## Spec closure definition

A spec is "closed" for admission purposes when:

- It is written, merged to `main` under
  `governance/design/phase2_substrate/tla/` (the directory is not
  created by this gate package; it is created when the *first* spec
  lands — see §Q-7 in the substrate package's open questions).
- It names the §22 contract and the AT/INV ids it bounds.
- It has a recorded model-check run (TLC or Apalache), with stated
  bounds and state-space size.
- Counterexamples are either zero, or each one is (a) accompanied by
  an AT addition in `governance/implementation/` that targets it,
  or (b) an explicit, reviewed "out of model" exclusion with
  justification in the spec header.
- A signer accepted it under §31.

---

## Spec-to-candidate precondition matrix

### TLA-1. Atomic Approval Barrier (C22.3)

- **Precondition for:** any substrate admission whose implementation
  alters the approval entry → barrier check → fence acquisition →
  execution-start gate.
- **Phase-2 reality:** no currently named substrate (A / B / C) or
  Rust candidate (R-1…R-6) touches C22.3 semantics directly.
  TLA-1 is therefore *justified* by §28 hardening priority but is
  **not** a hard precondition for any Phase-2 admission listed in
  `02`/`03`.
- **Admission rule:** if a later increment proposes to change C22.3
  adjudication, TLA-1 becomes a precondition.

### TLA-2. Capability Token Lifecycle (C22.6) — concurrent consume + revocation

- **Precondition for:**
  - Substrate A (A-ENTRY-3): the host-side capability broker
    introduces a new consumption path crossing host/guest.
  - Any future broadening of capability classes under §30.6.
- **Closure required:** zero counterexamples for the four properties
  in `phase2_substrate/06` TLA-2, under a state space that covers:
  concurrent consume vs revocation, crash before/after consume,
  cross-class escalation attempts, post-crash recovery.
- **Admission rule:** substrate A is **not admitted** until TLA-2 is
  closed. This is the hardest TLA+ precondition in Phase 2.

### TLA-3. WAL Durability + Seal Transaction Ordering (C22.1, C22.2)

- **Precondition for:**
  - Rust downshift R-3 (WAL frame parser / classifier): R3-ENTRY-2.
  - Rust downshift R-4 (ledger frame writer) when write ordering
    touches the nine-step routine.
- **Closure required:** zero counterexamples on the safety
  properties named in `phase2_substrate/06` TLA-3, across the
  enumerated crash windows.
- **Admission rule:** R-3 is **not admitted** until TLA-3 is closed.
  R-4 may be admitted without TLA-3 only if its changes are
  framing-only and do not affect ordering; that narrowness must be
  text-confirmed in the admission PR.

### TLA-4. Quarantine Run Lifecycle (§9.7) under crash + reaper

- **Precondition for:**
  - Substrate A (A-ENTRY-6): per-run stateful VM disk images
    + reaper.
  - APFS clonefile / phantom-workspace admission (see substrate
    package `05` — outside this file's per-candidate gates, but
    noted here).
- **Closure required:** zero counterexamples for "no run in
  `executing` is destroyed", "forensics-required runs are never
  silently destroyed", and the liveness property under fairness.
- **Admission rule:** substrate A and the phantom-workspace layer
  are **not admitted** until TLA-4 is closed.

### TLA-5. Replay Class Adjudication (C22.5) — multi-source evidence

- **Precondition for:**
  - Any substrate-A or substrate-B claim of `exact` replay class for
    a workload that previously ran at a lower class.
  - Any §22.5 policy broadening.
- **Closure required:** zero counterexamples on the monotonicity
  property (adding evidence cannot decrease class; removing evidence
  cannot increase class) and on "no input combination yields a class
  above what evidence permits".
- **Admission rule:** any substrate admission that *raises* a
  workload's replay class is **not admitted** until TLA-5 is closed.
  Admissions that do not raise class may proceed (with the §04
  downgrade evidence).

### TLA-6. Taint Propagation Graph (C22.11, §9.9)

- **Precondition for:**
  - Broadening of runner classes or validation lanes under §28 step 3.
  - Any substrate admission that introduces new causality-ref
    propagation surfaces (substrates A/B/C all potentially qualify).
- **Closure required:** zero counterexamples on "no illegal
  transition", "clearing a taint requires a governance event", and
  reachability of propagated taint from the originating source.
- **Admission rule:** if the substrate's admission PR argues it
  does not change the taint propagation surface, that argument must
  be made explicitly; otherwise TLA-6 is a precondition.

### TLA-7. Worker Run Lifecycle (§9.6) ↔ Quarantine Run Lifecycle (§9.7) coupling

- **Precondition for:** any increase of worker concurrency beyond the
  Phase-1 single-lane tracer bullet.
- **Phase-2 reality:** this package does **not** admit worker
  concurrency broadening. If a later increment proposes to broaden
  it, TLA-7 becomes a precondition. Until then, this is a justified
  but not-yet-required spec.

---

## Summary admission table

| Spec | Must-be-closed before admitting | Must-be-closed before admitting (Rust) | Notes |
|---|---|---|---|
| TLA-1 | — | — | Required if C22.3 adjudication changes later |
| TLA-2 | Substrate A | — | Host-side broker is the trigger |
| TLA-3 | — | R-3 (required); R-4 (conditional) | WAL parser / ordering surface |
| TLA-4 | Substrate A, phantom-workspace admission | — | Stateful per-run + reaper |
| TLA-5 | Substrate A/B claim raising replay class | — | Monotonicity must hold |
| TLA-6 | Any substrate that changes taint surface | — | Cross-substrate propagation |
| TLA-7 | Worker concurrency broadening (out of Phase-2 scope) | — | Phase-3+ |

---

## Admission disciplines for every spec

- **Named bounds.** Every spec lists finite bounds for its state
  space and the rationale for those bounds. "Unbounded" = denial.
- **Named properties.** Safety and liveness properties are
  enumerated; each is labeled; each has a model-check record.
- **Named exclusions.** Any "out of model" assumption is named in
  the spec header and justified.
- **Counterexample routing.** A counterexample becomes an AT
  addition in `governance/implementation/` — never a silent fix in
  code, never an informal patch to the spec.
- **No authority role.** A clean model-check does not override the
  audit ledger or the signoff gate. It is §3.4 evidence, not §31
  authority.

---

## What this section does not do

- It does not create `governance/design/phase2_substrate/tla/`.
- It does not write any spec.
- It does not pre-commit to TLC vs Apalache; the choice is made when
  the first spec lands, with a recorded rationale.
- It does not admit any substrate or Rust candidate.

Specs are admission preconditions, not admissions.
