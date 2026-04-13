# 04 — Future Replay Substrate Boundaries

Scope: substrate-level rules for what is captured, what is *honestly
not* captured, and how the audit binding stays consistent once Phase-2
substrates (§01) are introduced. This is design only; it does not
expand `ReplayAnchor` (23.12) or change `replay_classifier` semantics.

Constitutional anchors:
- §3.3 Explicit replay honesty
- §3.12 Explicit downgrade discipline
- §22.5 Replay Fidelity Contract (classes: exact / diagnostic /
  semantic / degraded / unreplayable)
- §23.12 ReplayAnchor (existing schema, unchanged)
- §31 Sign-off honesty

A central rule applies across every boundary below: **whenever the
substrate cannot honestly capture a dimension, the replay class is
downgraded by `replay_classifier`. Substrates do not get to claim
"exact" by silently filling gaps.**

---

## 1. Time

### Captured (admissible into ReplayAnchor)
- Wall-clock timestamps of stage transitions, host-side, with monotonic
  sequence number alongside.
- The host-side monotonic clock baseline used to derive durations.
- The substrate's *declared* clock policy (e.g., for substrate B/Wasm:
  `wasi:clocks` is denied unless an explicit capability grants it).

### Not captured (forces downgrade or explicit policy)
- Real-time wall clock observed *inside* a Wasmtime/WASI guest unless
  the host explicitly granted a deterministic clock shim.
- Real-time wall clock *inside* a `Virtualization.framework` Linux
  guest. Guest time is treated as untrusted; only the host-observed
  enter/exit timestamps are authority.
- Sub-microsecond ordering on multi-core macOS — not assumed.

### Boundary rule
- Time-sensitive validation outputs (e.g., a test that depends on a
  freshness window) are flagged at validation policy. If the substrate
  cannot pin time, the receipt is admissible only for `diagnostic`
  replay or below.
- "Exact" replay across time **requires** all in-guest time sources to
  have come from a host-deterministic clock shim whose seed/policy is
  recorded in `environment_fingerprint`.

---

## 2. Randomness

### Captured
- Any randomness consumed by validators *must* be drawn from a
  named, host-issued PRNG with a recorded seed and algorithm class
  (e.g., `chacha20-prng-v1`, seed bytes, draw count).
- The seed is bound into `ReplayAnchor.environment_fingerprint` and
  referenced by `version_tuple_hash` composition where applicable.

### Not captured
- Ambient `/dev/urandom` reads inside any guest substrate. Guests are
  denied OS RNG by default.
- Hardware RNG paths (RDRAND-equivalent) — not assumed exposed.

### Boundary rule
- A validator that consumes randomness without going through the
  host-issued PRNG path is *non-admissible* for exact replay. The
  classifier downgrades to `diagnostic` at best, and emits a
  divergence note explaining the missing seed binding.
- Wasmtime/WASI: `random_get` is denied by default; an explicit
  capability is required and the granted PRNG is the host-seeded one.
- `Virtualization.framework`: a deterministic in-guest seed-injection
  path is required for any "exact" claim; otherwise downgrade.

---

## 3. External worker determinism

External worker = anything outside the host control-plane process:
substrate B (Wasm), substrate A (`Virtualization.framework`), or
substrate C (Linux/KVM sidecar / remote worker) per §01.

### Captured
- The substrate identifier and version (engine version, base image
  hash, hypervisor build) recorded in `environment_fingerprint`.
- The capability tokens consumed (single-use, scoped) and the audit
  records around enter/exit.
- A host-computed digest of the bytes the worker returned, bound
  before any conversion into authority artifacts.

### Not captured (and explicitly honest about it)
- Apple Silicon micro-architectural variance (cache state, branch
  predictor, NEON/AMX scheduling). Even pinning the base image and
  toolchain does not give bit-identical floating-point in the general
  case.
- Cross-host bit-identical output for substrate C (sidecar / remote).
  §5 already declares cross-platform bit-identical replay is not
  assumed.
- Internal scheduling of multi-threaded test runners. Where threading
  is needed, the receipt is downgraded unless the worker is run
  single-threaded under explicit policy.

### Boundary rule
- Substrate A: "exact" replay is admissible only when (i) base image
  hash matches, (ii) deterministic clock + seed shims were used,
  (iii) the workload was run single-threaded *or* with a recorded
  scheduler-pinning policy, and (iv) host re-validation of returned
  bytes matches. Otherwise: `semantic` or `degraded`.
- Substrate B: "exact" is the default when no nondeterministic
  capability was granted.
- Substrate C: "exact" is **never** claimed automatically. Cross-host
  workloads default to `semantic` and require an explicit, audited
  proof bundle to claim higher (§22.5 equivalence rule).

---

## 4. Audit binding

This is the tightest boundary: regardless of substrate, the audit
ledger remains the single host-side, append-only authority surface.

### Required bindings (every substrate, every run)
- `AuditRecord` for substrate enter, with: substrate id, substrate
  version, base-image/engine hash, capability token id consumed,
  policy version, declared time/random/scheduler shim policy.
- `AuditRecord` for substrate exit, with: exit class
  (`clean`/`failed`/`tainted`), bytes-returned digest, host
  re-validation result digest, downgrade flag and reason if any.
- `ReplayAnchor` is minted by the host *only* after the exit record
  is durable and the substrate's contributions have been
  re-validated against schema.
- `version_tuple_hash` of every artifact crossing the substrate
  boundary is computed host-side, never inside the substrate.

### Forbidden
- Any substrate writing directly to the audit ledger.
- Any substrate minting `ReplayAnchor`, `ApprovalArtifact`,
  `CapabilityToken`, or `Revision`/`SnapshotRoot`.
- Any "trust the worker's self-report of clean exit". Exit class is
  determined host-side from observed evidence and host re-validation.

### Drift-and-downgrade rule
- If any of the four binding dimensions (time, randomness, worker
  determinism, audit binding) cannot be satisfied at the level the
  validator's policy requires, `replay_classifier` downgrades the
  classification and emits a `DriftEventRecord` (23.19) with the
  exact dimension that failed.
- Downgrade is **never** silent. §3.12 governs; §31 sign-off rejects
  any substrate whose downgrade events are not visible in audit.

---

## Summary boundary table

| Dimension | Substrate B (WASI) | Substrate A (Apple VM) | Substrate C (Linux KVM / remote) |
|---|---|---|---|
| Time pinning | host clock shim or denied | host clock shim required for exact | best-effort; usually downgrade |
| Randomness | host-seeded PRNG only | host-seeded PRNG required for exact | host-seeded PRNG required, plus proof bundle for exact |
| Worker determinism | high (single-threaded, no IO) | medium-high (single-thread + image hash) | low; default `semantic` |
| Audit binding | host writes only | host writes only | host writes only |

Net effect: introducing Phase-2 substrates does **not** widen exact
replay claims. It *narrows* them honestly and routes everything else
through `replay_classifier`'s downgrade path, which is exactly what
§22.5 requires.
