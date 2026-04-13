# 07 — Unresolved Blockers vs Recorded Risks

Scope: a disciplined separation between what is a **true blocker**
(would prevent the promotion-gate package itself from being honest
or usable) and what is a **recorded risk** (a real but non-blocking
uncertainty that has been routed into the right gate precondition
or admission criterion).

This file matters because "blocker" and "risk" are different
governance verdicts. A blocker stops this package. A recorded risk
does not — it is captured in the package as a named precondition
that a future admission PR must clear.

Constitutional anchors: §3.10, §3.14, §27, §31.

---

## True blockers

**None.**

Every dimension required to write a tight, honest phase-2
promotion-gate package is satisfiable from the existing baseline:

- the v11 constitution,
- the v11 narrow-path implementation foundation,
- the merged phase-2 substrate design package at
  `governance/design/phase2_substrate/`,
- the merged narrow-path hardening increments and the AT-027 budget
  governance increment.

No constitutional ambiguity prevented defining an evidence bar. No
missing baseline artifact prevented writing a per-substrate or
per-Rust-candidate entry criterion. No contradiction between the
constitution and the foundation required resolution in this
increment.

Consequently: this package is not blocked, nor does it introduce any
blocker that would prevent a future substrate admission from being
evaluated against it. The per-candidate gates in `02`/`03` and the
TLA+ preconditions in `05` are each reachable.

---

## Recorded risks (non-blocking to the gate; preconditions to
future admissions)

Each item below is a real uncertainty carried forward from the
phase-2 substrate design package's open-questions ledger (Q-1…Q-7).
Each is routed to an explicit admission-time precondition in this
package rather than left ambient.

### R-risk-1. Bit-identical replay across Apple-Silicon variants

Source: `phase2_substrate/07` Q-1. Micro-architectural variance on
M-series hardware (NEON/AMX scheduling, cache effects) means
floating-point and timing-sensitive workloads cannot be guaranteed
bit-identical across two machines of different generations.

- **Routed to:** `04` §3 (external worker determinism) and
  `02` A-ENTRY-5 (environment fingerprint binding) and `05` TLA-5
  (replay class monotonicity).
- **Admission consequence:** a substrate A admission that proposes
  to raise workloads to `exact` class must satisfy the §04 evidence
  matrix for the specific hardware class, or the admission is denied.
- **Not a blocker to this package** because the gate does not claim
  bit-identity is achievable; it requires that any `exact` claim
  under substrate A name the hardware-class policy that makes it
  honest.

### R-risk-2. APFS clonefile semantics under concurrent quarantine churn

Source: `phase2_substrate/07` Q-2. Failure-mode behavior of
`clonefile(2)` under high concurrency, near-disk-full states, and
rapid create/destroy cycles is documented at the interface level
but not at the failure-mode level.

- **Routed to:** the phantom-workspace admission gate (outside the
  per-candidate gates in this package; see `phase2_substrate/05`),
  reinforced by `05` TLA-4 (quarantine run lifecycle under crash +
  reaper).
- **Admission consequence:** phantom-workspace admission requires
  TLA-4 closure plus the §5.4 disk-budget honesty already named
  in the substrate design.
- **Not a blocker** to this gate package; any admission that depends
  on clonefile empirical behavior is deferred-pending-evidence until
  that behavior is measured.

### R-risk-3. Capability broker host/guest wire format and reaper

Source: `phase2_substrate/07` Q-4. Substrate A introduces a
host-side broker that translates host-issued, single-use capability
tokens into bounded effect handles inside the guest. Wire format,
crash-window durability, and reaper behavior are open.

- **Routed to:** `02` A-ENTRY-3 (host-side capability broker design
  closed) and A-ENTRY-7 (crash-window classification for broker),
  paired with `05` TLA-2 (capability token lifecycle).
- **Admission consequence:** substrate A is not admitted until the
  broker design is closed and TLA-2 is closed.
- **Not a blocker** to this gate package; the gate explicitly makes
  the broker a precondition of admission rather than a precondition
  of the gate.

### R-risk-4. WASI PRNG and clock shim canonicalization

Source: `phase2_substrate/07` Q-5. Wasmtime/WASI can deny
`random_get` and clock APIs by default, but the shape of the
host-issued shim (algorithm, seeding API, draw accounting in
`environment_fingerprint`) is not yet pinned.

- **Routed to:** `02` B-ENTRY-2 (PRNG/clock shim canonicalization
  decided) and `04` §1 + §2 (time and randomness dimensions).
- **Admission consequence:** substrate B is not admitted until
  Q-5's short follow-up design note is merged and the named fields
  are populated in `environment_fingerprint`.
- **Not a blocker** to this gate package; the gate names Q-5 as the
  B-ENTRY-2 precondition rather than resolving Q-5 itself.

### R-risk-5. Disk-budget accounting for clone divergence

Source: `phase2_substrate/07` Q-6. APFS clonefile is O(1) at clone
time but per-block divergence on write can grow disk usage
unpredictably under churn; §5.4 demands disk governance but the
exact accounting model is open.

- **Routed to:** the phantom-workspace admission gate (substrate
  package `05`), reinforced by `01` PR-6 (evidence closure /
  ledger throughput baselined — adjacent baseline discipline).
- **Admission consequence:** phantom-workspace admission requires a
  measured accounting model.
- **Not a blocker** to this gate package.

### R-risk-6. Code-signing / notarization for VM guest images

Source: `phase2_substrate/07` Q-3. Distribution of base images for
substrate A intersects Apple notarization, Gatekeeper, and Endpoint
Security policy; the constitution does not pre-decide this.

- **Routed to:** explicit **non-scope** of this package and of the
  substrate package. Flagged here only to ensure it does not
  accidentally re-enter via a substrate admission PR.
- **Admission consequence:** a substrate A admission PR that
  bundles notarization or packaging decisions trips §6.5 non-scope
  bundling and is denied on that basis alone.
- **Not a blocker** to this gate package.

### R-risk-7. Physical location of TLA+ specs

Source: `phase2_substrate/07` Q-7. Where specs physically live is
deferred. Proposal: `governance/design/phase2_substrate/tla/`,
created when the first spec lands.

- **Routed to:** `05` (TLA+ admission targets and preconditions),
  which names the directory but does not create it in this
  increment, preserving the discipline of "no directory suggests
  work in progress".
- **Admission consequence:** the first spec PR creates the
  directory, ending the risk. Until then, it stays a recorded risk
  with no hidden work.
- **Not a blocker** to this gate package.

---

## Why none of the above blocks this package

A blocker, in this package's vocabulary, is one of:

- a constitutional ambiguity that prevents defining an evidence bar,
- a missing baseline artifact without which a promotion gate cannot
  be written honestly,
- a contradiction between the constitution and the implementation
  foundation,
- or an unresolved open question that would have to be resolved
  *before* the gate itself could be coherent.

Risks R-risk-1 through R-risk-7 are none of those. Each is an
*empirical* or *implementation-detail* uncertainty about a future
substrate or a future broker. The correct place to resolve each is
the admission-time evidence it is routed to, not the gate package.

Every risk above has been named with:

- its source in the substrate package,
- its routing into a specific precondition in `02`/`03`/`04`/`05`,
- its admission consequence if unresolved,
- and an explicit statement that it does not block this package.

That routing is exactly what a promotion-gate package is supposed to
do under §27 and §3.14.

---

## Honest residuals statement

- This package does **not** pretend that R-risk-1 through R-risk-7
  are resolved.
- This package does **not** pretend that any phase-2 substrate
  admission is authorized. No admission is authorized by this
  package. Every admission requires its per-candidate gate to close.
- This package **is** honestly review-ready as a promotion-gate
  design. It is explicitly **not** review-ready as an implementation
  plan and authorizes no implementation work in `kernel/` or in any
  substrate of the phase-2 design package.

The ledger of "what is a true blocker" is therefore empty. The
ledger of "what is a recorded risk" has seven entries, each with a
named route to a future admission gate. That is the intended state
of a design-only promotion-gate package under §3.10 and §31.
