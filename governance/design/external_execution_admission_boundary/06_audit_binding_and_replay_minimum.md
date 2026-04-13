# 06 — Audit Binding and Replay Minimum

Scope: the **exact minimum** audit binding and replay evidence any
external executor must support before its outputs are admissible.
This file complements `phase2_promotion_gate/04` (which sets the
phase-wide evidence bar before any substrate is admitted) by pinning
the *per-invocation* binding minimum at the boundary itself.

This is design only. It does not change `AuditRecord`, `ReplayAnchor`,
`DriftEventRecord`, or any other receipt shape. It pins how existing
fields are *populated* per invocation.

Constitutional anchors: §3.3, §3.12, §22.1, §22.5, §22.10, §23.12,
§23.14, §23.19, §31.

---

## 1. The four binding dimensions

Every executor invocation is bound on four dimensions. The same
dimensions appear in `phase2_substrate/04` and
`phase2_promotion_gate/04`; this file says what the *minimum* evidence
on each dimension must look like at the per-invocation level.

| Dimension | What is bound | Where it lives | Failure mode if missing |
|---|---|---|---|
| Time | host-observed enter/exit timestamps + monotonic seq + declared in-executor clock policy | `AuditRecord(enter/exit)`, `environment_fingerprint` | downgrade D-TIME |
| Randomness | host-issued PRNG identity + seed + draw-count budget | `environment_fingerprint` | downgrade D-RAND |
| Worker determinism | executor identity, version, base-image/engine hash, scheduler/threading policy | `environment_fingerprint` | downgrade D-WORKER |
| Audit binding | enter+exit `AuditRecord` pair, capability token id consumed, handle catalog digest, bytes-returned digest | `AuditRecord`, `ReplayAnchor.environment_fingerprint` | reject R-AUDIT-INCOH or downgrade D-AUDIT |

These dimensions are *not* optional. An invocation that cannot bind
all four at the validator's required class is reject / downgrade /
defer per file `05`.

---

## 2. Time dimension minimum

### 2.1 Captured per invocation (host-observed, authoritative)

- Wall-clock timestamp at session start (host-observed at the moment
  the broker exposes the first effect handle).
- Wall-clock timestamp at session exit (host-observed at the moment
  the host receives the exit signal).
- Host-side monotonic sequence number for both transitions.

### 2.2 Captured per invocation (declared shim policy)

- The exact in-executor clock policy: one of
  - `denied` (no clock surface granted; default for all executors)
  - `host-shim:<id>` (host-deterministic clock shim; the shim's
    identity and policy version recorded in `environment_fingerprint`)
  - `executor-native` (the executor read native clock; *only* legal
    for substrates where this can be honestly bounded, and *always*
    forces D-TIME downgrade because the host cannot replay it)

### 2.3 Forbidden

- Any invocation that *uses* a clock the host did not authorize via
  one of the above policies → `exited_tainted` (file `03.6.3`).
- Any invocation that claims `exact` replay class while running with
  `executor-native` clock → boundary violation (`08.5`).

### 2.4 Minimum for `exact` class

- `host-shim:<id>` clock policy with the shim's seed/policy bound;
  AND
- host-observed enter/exit timestamps; AND
- monotonic seq numbers from the host.

Anything less = downgrade D-TIME.

---

## 3. Randomness dimension minimum

### 3.1 Captured per invocation

- The PRNG algorithm class (e.g., a pinned ChaCha20-class), the
  seed bytes, and the draw-count budget the executor was granted.
- The shim handle identity exposed to the executor.

### 3.2 Forbidden

- `/dev/urandom` reads inside any executor (or substrate-equivalent
  ambient RNG).
- Hardware RNG paths (RDRAND-equivalent).
- Any randomness consumption not routed through the broker shim.

### 3.3 Minimum for `exact` class

- Host-issued PRNG handle was the *only* randomness source granted;
  AND
- Algorithm class, seed, and draw count are bound into
  `environment_fingerprint`.

Otherwise → downgrade D-RAND.

---

## 4. Worker determinism dimension minimum

### 4.1 Captured per invocation

- Executor identity (e.g., `wasmtime-vX.Y`, `applevm:linux-base@<hash>`,
  `sidecar:<host-id>`, `clonefile-helper:<id>`).
- Executor version (engine version, hypervisor build, image hash).
- Threading / scheduler policy (single-threaded by default; recorded
  pinning policy if multi-threaded).
- Substrate-specific micro-architectural notes where they affect
  determinism (e.g., AMX/NEON path policy on Apple Silicon —
  acknowledged unbounded per `phase2_substrate/04 §3`).

### 4.2 Forbidden

- Multi-threaded execution without a recorded, host-evaluated
  scheduler-pinning policy → automatic downgrade D-WORKER.
- Subprocess spawn (where substrate permits any) without inheritance
  of the same boundary → `exited_tainted` (file `04 F-6`).

### 4.3 Minimum for `exact` class

- Substrate B (Wasmtime/WASI): single-threaded, no nondeterministic
  capability granted, engine version bound.
- Substrate A (Apple-VM): base image hash matches host's canonical
  record, single-threaded or recorded scheduler pinning, host clock/
  PRNG shims used.
- Substrate C (sidecar/remote): **never** automatically `exact`. A
  proof bundle (signed, audited) is required to claim higher than
  `semantic`, per `phase2_substrate/04 §3`.
- Clonefile helper: process-level worker; subject to substrate B/A
  posture depending on what the helper actually does — almost always
  bounded enough to qualify if the other dimensions hold.

---

## 5. Audit-binding dimension minimum

### 5.1 Required per invocation, host-authored

- `AuditRecord(enter)` with: executor id, version, base-image/engine
  hash, capability token id consumed, declared shim policies (time,
  random, scheduler), handle catalog digest, budget envelope.
- `AuditRecord(exit)` with: exit class
  (`clean`/`failed`/`tainted`), bytes-returned digest, host re-
  validation result digest, downgrade vector and reason if any,
  resource-accounting summary (host-observed wall-time, CPU, peak
  RSS, peak disk).
- `ReplayAnchor` minted host-side after exit `AuditRecord` is durable
  and host re-validation has run; binds the
  `environment_fingerprint` populated above and the
  `version_tuple_hash` host-composed at G-7.
- One `DriftEventRecord` per dimension the classifier downgraded
  (file `05 §4`).
- `TaintRecord`(s) for any propagated taint (file `05 §G-5`).

### 5.2 Forbidden

- Any executor writing to the audit ledger (file `04 F-4`).
- Any executor minting `ReplayAnchor` (file `04 F-3`).
- Any "exit succeeded" claim from the executor that suppresses the
  host's classification (file `04 F-12`).
- Streaming `AuditRecord` emission (host composes both records as
  pairs; no in-flight admission).

### 5.3 Minimum for any admission at all

The enter/exit pair must be **complete** (all required fields
populated host-side) and **durable** (on the §22.1 WAL path) before
the candidate enters ingress (file `05 G-1`).

A pair that is durable but incomplete → reject R-AUDIT-INCOH.
A pair that is complete but missing optional fields → downgrade
D-AUDIT (per `05 §4`).

---

## 6. Replay minimum per executor (substrate-shape view)

This table is the per-invocation expression of
`phase2_substrate/04` §"Summary boundary table", restated as the
minimum binding that must already exist at the boundary before any
executor of the substrate shape is even attempted.

| Dimension | Wasmtime / WASI | Apple `Virtualization.framework` | Linux/KVM sidecar or remote | APFS clonefile helper |
|---|---|---|---|---|
| Time policy | `denied` or `host-shim:<id>` | `host-shim:<id>` required for `exact`; otherwise downgrade | `host-shim:<id>` typically still downgrade | inherits host process's posture |
| Randomness policy | `denied` or host-PRNG-only | host-PRNG required for `exact` | host-PRNG required *and* proof bundle for `exact` | host-PRNG required if any randomness is used |
| Worker determinism | high (single-threaded, no IO) | medium-high (single-thread + image hash) | low; default `semantic`; never automatic `exact` | high (process boundary, clone is read-only) |
| Audit binding | host-only authoring | host-only authoring | host-only authoring + signed transport binding | host-only authoring |

This table is *not* a class promise. It is a *minimum*: an
invocation that does not at least achieve this binding is denied
admission per file `05`. Achieving the binding does not by itself
admit; admission still goes through `phase2_promotion_gate`.

---

## 7. Replay-class admissibility per executor

### 7.1 `exact`

Admissible only when all four dimensions are at their `exact`
minimum *and* the validator's policy permits `exact` for this
workload. An admission of `exact` while any dimension is short →
`08.5` (silent class raise) violation.

### 7.2 `diagnostic`

Admissible when audit-binding dimension is complete and the other
three are bound to at least their `diagnostic` minimum (e.g.,
host-observed enter/exit timestamps even if in-executor clock policy
is `executor-native`).

### 7.3 `semantic`

The default for substrate C; admissible when host re-validation of
returned bytes is complete and audit-binding is complete, even if
worker-determinism is low.

### 7.4 `degraded`

Admissible when any one of the four dimensions has emitted a
downgrade and the validator's policy permits `degraded`. Otherwise
the candidate is rejected.

### 7.5 `unreplayable`

Admissible only when the validator explicitly authorizes
`unreplayable` admission *and* a `DriftEventRecord` for every
unsatisfied dimension is emitted.

In every case the class is decided host-side by `replay_classifier`,
not by the executor. The executor's posture cannot raise the class.

---

## 8. Per-invocation audit sufficiency (re-statement)

A run is admissible into the eight-stage signable path only if the
host can answer, **from audit alone**, the eight questions in
`03 §8`. The answers themselves live in:

1. `AuditRecord(enter).executor` — id, version, image/engine hash
2. `AuditRecord(enter).capability_token_id` and `.policy_version`
3. `AuditRecord(enter).handle_catalog_digest`
4. `AuditRecord(enter).shim_policy` (time, random, scheduler)
5. `AuditRecord(enter).budget_envelope` and
   `AuditRecord(exit).resource_summary`
6. `AuditRecord(exit).exit_class` and `.evidence`
7. `DriftEventRecord(*).dimension` and `.reason`
8. `ReplayAnchor.environment_fingerprint` (which composes the handle
   catalog digest and the bytes-returned digest) and the host-
   composed `version_tuple_hash`

These are *uses* of existing fields. No field is added. No field is
re-shaped.

---

## 9. Net statement

The boundary's audit and replay minimum are the smallest set of
host-authored bindings that allow `replay_classifier` to honestly
decide a class and the §31 sign-off to honestly evaluate sufficiency.
Anything below this minimum is denial. Anything claimed above the
evidence is overclaiming and is denial. The minimum is itself
*necessary*, not sufficient — `phase2_promotion_gate` per-candidate
evidence and §31 sign-off still apply on top.
