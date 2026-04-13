# 01 — Future Execution Substrate on Darwin

Scope: substrate options for **validation-time and patch-application
execution** under the existing eight-stage signable path. Nothing here
broadens runner classes or admits new mutation classes.

Constitutional anchors:
- §22.4 Validation Quarantine Enforcement Contract
- §22.6 Capability Token Lifecycle Contract
- §22.11 Taint Propagation Graph Contract
- §5.5 macOS platform-specificity rule
- §27 substrate strategy (mature first, internalize on evidence)

Phase-1 baseline today: local macOS runner with policy-governed
constraints (`validation/quarantine/runner_adapter.py`), explicitly
classified as **bounded quarantine guarantee** (not container-equivalent).

The choices below are *future* substrates considered for Phase 2/3
hardening. Each is described by what it would own, what it would not
own, and the evidence bar required to promote it from candidate to
admitted substrate.

---

## A. Apple `Virtualization.framework` (Darwin-native VM)

### What it would own
- A disposable **Linux guest VM** for running the validation lane and
  patch build/test workloads that need a real Linux kernel surface
  (network namespacing, cgroups, deterministic libc, real `/proc`).
- Per-run ephemeral root disk image (cloned from a sealed base image
  whose hash is bound into `ValidationReceipt.environment_fingerprint`).
- Network-off enforcement at the hypervisor boundary, not the process
  boundary (stronger than current macOS-native quarantine).
- macOS-host-side teardown of guest disk images and shared folders.

### What it would not own
- Authority. The kernel control plane never runs inside the guest.
- Truth. SQLite/WAL never crosses the hypervisor boundary; the guest
  has no write path to `kernel/stores/`.
- Capability issuance. Tokens are issued host-side and *consumed* via a
  narrow host-side broker; the guest only sees scoped, single-use
  effect handles.
- Replay anchor minting. The host audits guest exit and binds the
  receipt; the guest does not produce authority artifacts.

### Why it earns its place
- macOS-native, Apple-supported; first-party hypervisor on Apple
  Silicon. No third-party kernel extensions, no developer-tier
  workarounds.
- Crosses the §22.4 "network-off / host read-only / isolated caches /
  disposable filesystem layer / bounded resources / secret isolation"
  bar at a stronger guarantee level than process-level macOS
  sandboxing alone.
- Honest fit with §5.5 (macOS-specific isolation strategy must remain
  explicit) and §27 (mature, measurable, local-first substrate).

### Failure modes / cost
- Image freshness vs. determinism: base image must be content-addressed
  and re-derivable; otherwise replay environment fingerprint drifts.
- VM cold-start latency adds to validation lane time-to-receipt; not a
  correctness risk but a budget pressure under §5.2.
- Apple Silicon micro-architectural variance (e.g., AMX/NEON
  scheduling) is *not* eliminated — see §04 boundaries.

### Evidence bar to promote
- AT-010 / AT-011 re-run inside the guest with explicit network-off
  proof at hypervisor level.
- Documented base-image build pipeline whose output hash is
  reproducible across two host machines of the same hardware class.
- Crash-window classification (§22.1) re-validated for the host-side
  broker that mediates capability consumption across the boundary.

### Replacement trigger
Promote out of "candidate" only when a concrete failure of the
process-level quarantine guarantee surfaces (a real AT-010/AT-011
failure or audit downgrade), per §3.14 replacement-by-evidence.

---

## B. Wasmtime / WASI sandbox

### What it would own
- A *per-call* deterministic execution surface for **pure, bounded,
  compute-only** validation steps: schema validators, deterministic
  hashers, structured-diff coherence checks, replay classification
  arithmetic, future "small kernels" written in Rust.
- An in-process boundary for sandboxing untrusted *static* analyzers
  shipped as `.wasm` modules (no syscall surface, no network, no fs
  beyond explicitly granted preopens).

### What it would not own
- Anything requiring a real toolchain (compilers, package managers,
  language test runners). Those belong to substrate A.
- Any IO that needs `/proc`, real DNS, real subprocess management.
- Capability *issuance*; only consumption of bounded, scoped,
  pre-validated capability tokens by a host shim.

### Why it earns its place
- WASI gives a documented, auditable syscall surface — a much smaller
  attack and nondeterminism corpus than a full POSIX runner.
- Strong determinism story for "pure" validators: no wall clock leakage
  unless explicitly granted, no thread scheduler nondeterminism in the
  single-threaded guest model.
- Cheap to instantiate; can be the *first* sandbox crossed before any
  heavier substrate is engaged.

### Failure modes / cost
- WASI is not a Linux runner; build tools and most language test
  suites do not run here. This is a *complement* to A, not a
  replacement.
- Floating-point and SIMD determinism still depend on the host engine
  configuration; explicit pinning required (see §04).

### Evidence bar to promote
- A first identified validator that today runs in-Python and would
  measurably benefit (correctness or perf) from a Wasm boundary —
  e.g., a structured-diff coherence checker (§22.13) — is rewritten
  as Rust→Wasm, measured, and shows either a determinism win or a
  10x+ throughput win.
- No promotion is admitted on aesthetic grounds.

### Replacement trigger
Same posture as A: only adopt when an identified Phase-1/Phase-2
failure or measurement justifies it (§27, §3.14).

---

## C. Linux/KVM sidecar or remote worker

### What it would own
- A **same-host** Linux sidecar (UTM/QEMU/KVM where lawful, or a
  separate physical Linux host on the LAN) used only when a workload
  *cannot* run inside Apple's `Virtualization.framework` at the
  fidelity required (e.g., kernel features unavailable to a Darwin
  guest, hardware-accelerated paths that need a different host).
- Optionally, a **remote worker** (single, named, audited) for
  workloads that exceed local hardware budget per §5.2/§5.3.

### What it would not own
- Authority, truth, capability issuance, audit ledger, approval
  barrier, seal ordering — *none* of these cross the network. The
  sidecar/remote is a pure executor of pre-authorized work and
  produces only signed receipts and bounded artifacts the host
  re-validates.
- Any role in the eight-stage signable path beyond producing inputs to
  ValidationReceipt under host-issued, single-use capabilities.

### Why it earns its place
- An honest pressure-relief valve for §5.2 ("simultaneous
  inference + validation"): if the local box is the bottleneck, a
  governed sidecar is preferable to silently degrading lane quality.
- Keeps the kernel singular while admitting a strictly subordinate
  worker (matches §29 multi-vendor doctrine: "use them as
  replaceable workers; do not depend on them for authority").

### Failure modes / cost
- Network introduces a new failure / drift surface; every artifact
  that crosses must be signed and re-validated host-side.
- Replay exactness across hosts is *not* claimed (§5 baseline already
  warns "cross-platform bit-identical replay is not assumed").
- This is the first substrate that reintroduces a partition-failure
  class; the host must treat sidecar silence as `exited_failed`, not
  `exited_clean`.

### Evidence bar to promote
- Local-only path (A + B) must be measured to be insufficient for an
  identified, real workload before any sidecar is admitted.
- A signed, auditable transport (with `version_tuple_hash` binding) is
  designed and validated *before* a sidecar runs.

### Replacement trigger
This substrate is the **last** to be admitted under §27, §28, and
§30.6. It is a Phase-3+ candidate, not a Phase-2 default.

---

## Summary ownership table

| Layer | Owner candidate | Authority? | Truth? | Capability issuance? | Receipt source? |
|---|---|---|---|---|---|
| Pure deterministic validators | Wasmtime/WASI (B) | no | no | no | yes (host re-binds) |
| Linux toolchain validation | `Virtualization.framework` (A) | no | no | no | yes (host re-binds) |
| Out-of-budget / non-Darwin guest needs | Linux/KVM sidecar or remote (C) | no | no | no | yes (host re-binds) |
| Authority, approval, seal, audit | **Python control plane (host)** | yes | yes | yes | yes (sole signer) |

Constitutional posture: kernel sovereignty is preserved across all
three. None of A/B/C is an authority surface; each is a *bounded
executor* whose output enters the eight-stage path only via
host-mediated, capability-gated, audit-bound ingress.
