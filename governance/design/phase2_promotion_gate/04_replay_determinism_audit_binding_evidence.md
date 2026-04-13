# 04 — Replay / Determinism / Audit-Binding Evidence Bar

Scope: the **exact evidence** required to be in place before any
phase-2 substrate or Rust downshift candidate is promoted to
implementation. This file translates
`governance/design/phase2_substrate/04_replay_substrate_boundaries.md`
into a concrete pre-admission evidence bar.

Central rule, repeated for clarity: *Substrate admission does **not**
introduce the downgrade path; it relies on it being honest first.*

Constitutional anchors: §3.3, §3.12, §22.1, §22.2, §22.5, §23.12, §31.

---

## 1. Time dimension

### 1.1. Required evidence before any substrate introducing guest time

- Host-side monotonic clock baseline is already the sole authority
  for durations in `ReplayAnchor` and its referenced records.
- For any substrate that introduces guest time (A or B), the
  declared clock policy field is populated and bound into
  `environment_fingerprint`.
- A forced-drift test exists: changing the declared clock policy
  produces a distinct `environment_fingerprint` and the classifier
  downgrades any claimed `exact` to at most `diagnostic` when the
  substrate's clock source is unpinned.

### 1.2. Forbidden shortcuts

- **Implicit host-clock trust inside a guest.** Not admitted.
- **Guest wall-clock recorded silently as authority.** Not admitted;
  §3.3 / §3.12 violation.
- **`wasi:clocks` granted by default in substrate B.** Not admitted;
  deny-by-default is the floor.

### 1.3. Evidence artifact required

- A test that forces time drift and asserts the receipt downgrades
  correctly with a `DriftEventRecord` naming the time dimension.

---

## 2. Randomness dimension

### 2.1. Required evidence

- A single named host-issued PRNG class (e.g.,
  `chacha20-prng-v1`), with a declared seeding API, exists and is
  the only path any validator consumes.
- The seed bytes, algorithm class, and draw count are recorded in
  `ReplayAnchor.environment_fingerprint` — present on the receipt,
  not just documented.
- Wasmtime/WASI `random_get` is denied by default at engine
  configuration; grant is per-capability, per-call.
- `Virtualization.framework` guest has no `/dev/urandom` fall-through
  to host entropy without going through the declared shim.

### 2.2. Forbidden shortcuts

- **Ambient `/dev/urandom`.** Not admitted as a source for any
  validator whose output enters authority.
- **Hardware RNG paths (RDRAND, etc.).** Not assumed exposed; any
  reliance = denial.
- **"Seed baked into base image."** Not admitted; seed is per-run,
  bound into the receipt.

### 2.3. Evidence artifact required

- A test that runs a validator twice with the same seed and asserts
  identical receipt-level outputs; a second test that changes the
  seed and asserts divergent fingerprints and, where the validator
  is nondeterministic under seeding policy, a classifier downgrade.

---

## 3. External worker determinism dimension

### 3.1. Required evidence before admitting any substrate A / B / C

- The substrate identifier, substrate version, engine or hypervisor
  build hash, and base-image hash (where applicable) are recorded in
  `environment_fingerprint` on every receipt that crosses the
  substrate boundary.
- A host-computed digest of the bytes returned from the worker is
  recorded in audit **before** any conversion into authority
  artifacts.
- The scheduler/threading policy is declared (single-threaded
  unless explicitly and auditably widened).

### 3.2. Substrate-specific floors

- **Substrate A (Apple VM):** "exact" is admissible only when base
  image hash matches, deterministic clock + seed shims were used,
  workload ran single-threaded *or* with a recorded scheduler-pinning
  policy, and host re-validation of returned bytes matches. Every
  one of those is a test condition, not a docstring. Otherwise
  classification is `semantic` or `degraded`.
- **Substrate B (Wasmtime/WASI):** "exact" is the default only when
  no nondeterministic capability was granted. Any granted
  capability automatically downgrades the default, and that
  downgrade is tested.
- **Substrate C (Linux/KVM sidecar or remote):** "exact" is
  **never** claimed automatically. A proof bundle per §22.5 is
  required; absent the bundle, classification defaults to
  `semantic`. This default is tested.

### 3.3. Forbidden shortcuts

- **Trusting worker self-report of "clean exit".** Not admitted; exit
  class is determined host-side from observed evidence.
- **Cross-host bit-identical claim for substrate C.** Never admitted;
  §5 baseline already precludes it.
- **Silent widening of threading.** Any change from single-threaded
  to multi-threaded is an environment fingerprint change and a
  classifier input, not a quiet config tweak.

### 3.4. Evidence artifact required

- Per substrate, a test that forces a failure of one fingerprint
  dimension (substrate version bump, image hash mismatch, scheduler
  policy change) and asserts the classifier produces the correct
  class with a `DriftEventRecord` naming the dimension.

---

## 4. Audit binding dimension

### 4.1. Required evidence

- Every substrate enter/exit pair emits a pair of `AuditRecord`
  entries with: substrate id, substrate version, base-image / engine
  hash, capability token id consumed, policy version, declared
  time/random/scheduler shim policy, exit class, bytes-returned
  digest, host re-validation result digest, and downgrade flag +
  reason where applicable.
- `ReplayAnchor` minting happens host-side and only after the exit
  record is durable. A test forces exit-record non-durability and
  asserts no `ReplayAnchor` is produced.
- `version_tuple_hash` is computed host-side after every substrate
  boundary crossing.

### 4.2. Forbidden (every substrate, every candidate)

- Any substrate writing directly to the audit ledger = denial.
- Any substrate minting `ReplayAnchor`, `ApprovalArtifact`,
  `CapabilityToken`, `Revision`, or `SnapshotRoot` = denial.
- Any trust of worker self-report as authority = denial.

### 4.3. Evidence artifact required

- A test that attempts (in a synthetic harness, not production) to
  write to the audit ledger from "inside the substrate" and asserts
  the attempt is refused at the host boundary.
- A test that asserts `ReplayAnchor` content for a substrate run
  names the enter/exit `AuditRecord` ids.

---

## 5. Drift-and-downgrade wiring (pre-admission)

### 5.1. Required before any substrate admission

If any of the four dimensions above cannot be satisfied at the level
a validator's policy requires, `replay_classifier` downgrades the
classification and emits a `DriftEventRecord` (23.19) naming the
exact failing dimension. Not "ambient" — named.

### 5.2. Required test matrix

A matrix with one row per dimension × one column per substrate that
the admission PR may reference. Each cell is either:

- a cited test id that forces that dimension's failure and asserts
  the correct downgrade + drift event, **or**
- an explicit "N/A" with a reason (e.g., "substrate B does not
  introduce a guest time path because `wasi:clocks` is denied at
  engine configuration; see B-ENTRY-3").

An admission PR that references a matrix containing any unreferenced
cell = denial.

### 5.3. Forbidden shortcuts

- Silent downgrades (no `DriftEventRecord`) = §3.12 violation =
  denial.
- Downgrade text that does not name the failing dimension = denial.
- Catch-all "something drifted" drift events = denial.

---

## 6. Replay class monotonicity (evidence)

### 6.1. Required before any admission that changes substrate inputs

Adding evidence does not decrease class; removing evidence does not
increase class. This is TLA-5's property (`05`). Before admission:

- The A/B harness for the candidate demonstrates monotonicity on the
  corpus (adding an evidence input never drops the class; removing
  one never raises it).
- No new "shortcut" input is introduced that would allow a class
  higher than supported.

### 6.2. Evidence artifact required

- Either the TLA-5 spec closure, or a differential test run covering
  adjacent evidence combinations across the corpus. TLA-5 is the
  preferred artifact; the test alternative is admissible only as a
  pre-TLA-5 bridge.

---

## 7. Scope limits of this evidence bar

- This file does **not** change `ReplayAnchor` shape.
- This file does **not** introduce new replay classes beyond the
  §22.5 set.
- This file does **not** introduce new `DriftEventRecord`
  dimensions beyond the four named.
- This file does **not** authorize any substrate admission by itself;
  its purpose is to enumerate what the per-substrate gate (`02`)
  and per-Rust-candidate gate (`03`) must rely on already being
  true.

Without the named evidence above in place, all substrate and Rust
downshift admissions are denied by default, regardless of how
attractive the roadmap looks.
