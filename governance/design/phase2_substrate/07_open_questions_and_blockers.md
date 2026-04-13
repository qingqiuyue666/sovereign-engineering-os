# 07 — Open Questions, Ambiguities, and Blocker Audit

This file separates *true* blockers (would prevent the design package
from being honest) from *open questions* (legitimate Phase-2 unknowns
that the design package documents rather than resolves).

## True blockers

**None.**

Every dimension required to write this design package was satisfiable
from the existing constitution and Phase-1 implementation foundation.
No constitutional ambiguity prevented producing a tight design.

## Open questions (documented, not blocking the design)

### Q-1. Bit-identical replay across Apple-Silicon variants
Even with substrate A (Apple `Virtualization.framework`) plus pinned
base image plus host clock/PRNG shims, micro-architectural variance
(e.g., scheduling of NEON/AMX paths, cache effects) means
floating-point and timing-sensitive workloads cannot be guaranteed
bit-identical across two M-series machines of different generations.

- Disposition: documented in `04` (substrate determinism boundary).
  Affects what may be claimed as "exact" replay.
- Resolution path: empirical measurement during Phase-2 hardening on
  the real hardware corpus, then either (a) declare a hardware-class
  policy that matches reality, or (b) restrict "exact" to
  integer/byte-deterministic workloads only.
- Not a design blocker.

### Q-2. APFS clonefile semantics under heavy concurrent quarantine churn
Behavior of `clonefile(2)` under high concurrency, near-disk-full
states, and rapid create/destroy cycles is documented at the
*interface* level but not at the *failure-mode* level needed for §22.4
"per-run disposable workspace" guarantees.

- Disposition: documented in `05` with explicit guarantees-required
  list and failure modes.
- Resolution path: small empirical study during Phase-2 hardening
  before clonefile is admitted as a substrate layer.
- Not a design blocker.

### Q-3. Code-signing / notarization story for `Virtualization.framework` guests
Distribution of base images for substrate A on developer/team machines
intersects Apple notarization, Gatekeeper, and (eventually) Endpoint
Security policy. The constitution does not pre-decide this.

- Disposition: out of scope for *this* design package per the README
  non-scope (release breadth, packaging). Flagged here so it is not
  mistakenly attempted later as a quiet substrate-design item.
- Resolution path: handled in a separate, future packaging-design
  package.
- Not a design blocker.

### Q-4. Capability broker boundary across the host/guest line (substrate A)
Substrate A introduces a host-side broker that translates
host-issued, single-use capability tokens into bounded effect handles
visible inside the guest. The exact wire format, transport durability
(`AT-006`-class crash windows around the broker), and broker reaper
behavior are open.

- Disposition: enumerated as part of substrate A's evidence bar in
  `01`. Touches §22.6 and §22.1.
- Resolution path: paired with TLA-2 (`06`) and the Rust WAL
  classifier candidate (R-3 in `03`) when the broker is implemented.
- Not a design blocker.

### Q-5. PRNG / clock-shim canonicalization for Wasmtime/WASI
Substrate B can deny `random_get` and clock APIs by default, but the
*shape* of the host-issued shim (algorithm, seeding API, draw
accounting in `environment_fingerprint`) is not yet pinned.

- Disposition: enumerated in `04` as a determinism boundary.
- Resolution path: pin in a small follow-up design note when the
  first WASI-resident validator is admitted under `03`'s R-1/R-2
  evidence bars.
- Not a design blocker.

### Q-6. Disk-budget accounting model for clone-divergence
APFS clonefile is O(1) at clone time but per-block divergence can
grow disk usage unpredictably. §5.4 demands disk governance, but the
exact accounting model (when divergence is sampled, how it is
attributed back to a run) is open.

- Disposition: documented in `05` failure-modes-to-design-against.
- Resolution path: empirical sampling during Phase-2 hardening.
- Not a design blocker.

### Q-7. Where TLA+ specs physically live
Decision deferred. The proposal is `governance/design/phase2_substrate/tla/`
when specs are first written. The directory is **not** created now to
avoid suggesting work in progress.

- Disposition: §06 says specs are not written in this increment.
- Not a design blocker.

## Why none of the above blocks the design

A blocker would be a constitutional ambiguity, a missing baseline
artifact, or a contradiction between the constitution and the Phase-1
foundation that prevented honest substrate boundary-drawing. Q-1
through Q-7 are *open empirical/engineering questions about future
substrates*. Each is properly named, scoped, and routed to the right
later increment with the right evidence bar. That is exactly what a
design package is supposed to do under §27 and §3.14.

## Honest residuals statement

- This package does not pretend the open questions are resolved.
- This package does not pretend that Phase-2 substrate adoption is
  authorized.
- This package is review-ready as a *design* and is honestly *not*
  review-ready as an implementation plan that authorizes work.
