# 04 — Allowed I/O Surfaces and Forbidden Mutation Surfaces

Scope: the **exact** list of I/O surfaces an external executor may
touch, and the **exact** list of mutation surfaces it must never
touch. The list is intentionally short. Anything not on the allowed
list is denied at the boundary by §3.2 (default deny).

This file is per-executor-shape-agnostic: the same surfaces apply to
Wasmtime/WASI, Apple-VM Linux guests, Linux/KVM sidecars/remote
workers, and APFS clonefile-backed phantom workspace helpers, with
the per-substrate technical mapping noted where useful.

Constitutional anchors: §3.1, §3.2, §3.11, §22.4, §22.6, §22.8,
§22.10, §22.11, §22.13.

---

## 1. Allowed input surfaces (read-only)

An executor may **read** only from surfaces explicitly issued to it
through broker effect handles (file `02`). Read access is bounded,
scoped, and revocable. The four allowed input surfaces:

### IN-1. Preopened input bytes

A bounded set of read-only file descriptors / read-only mounts /
clone-mounts the broker pre-exposed. The executor may not `open()` /
`open-at()` outside the preopen set. WASI: curated preopens.
Apple-VM: virtio-fs preopens (read-only). Sidecar: signed payload
attachments. Clonefile helper: a single read-only mount of the clone
root.

### IN-2. Capability-issued shim handles

Time, randomness, and budget-status handles per file `02.2` and
`06.2`/`06.3`/`06.5`. These are the *only* sources of clock value,
randomness, and budget information the executor may consume; ambient
sources are denied (file `4` below).

### IN-3. Host-supplied environment fingerprint subset

A canonicalized, host-defined subset of `environment_fingerprint`
made available read-only (e.g., the executor identity and version
the host is invoking). This is informational; the executor cannot
modify it, and host-side `version_tuple_hash` composition is not
influenced by what the executor reads from this surface.

### IN-4. Pre-staged candidate inputs from prior stages

Read-only access to bytes the host has previously admitted from
prior eight-stage path stages (e.g., a `Revision`'s file content for
a validator to check), exposed only as bounded preopens.

These four are the entire input surface. There is no IN-5.

---

## 2. Allowed output surfaces (bounded, write-once)

An executor may **write** only to surfaces explicitly issued to it
through broker effect handles. Three allowed output surfaces:

### OUT-1. Per-run write-once output area

A single, pre-allocated, ephemeral path the host scrapes after exit.
The executor may write files inside it; the host re-validates them
on ingress (file `05`). The output area is reaped on exit per the
§22.4 disposable-layer guarantee.

### OUT-2. Per-run candidate byte buffer

A bounded byte buffer the executor may stream to (subject to budget
caps). The host computes a digest at exit (file `05.2`) and ingests
it as candidate material.

### OUT-3. Exit signaling

An `exit()` (or substrate-equivalent) with a numeric status the host
observes. The executor may not author its own classification (file
`03.5`).

These three are the entire output surface. There is no OUT-4. In
particular there is no "executor-initiated audit emit", no
"executor-initiated capability mint", no "executor-initiated
`DriftEventRecord`".

---

## 3. Allowed inter-component surfaces

The executor may **not** initiate communication with anything other
than the host, through the broker's effect handles. The exhaustive
list of allowed inter-component crossings:

- IN-1 / IN-2 / IN-3 / IN-4 read crossings (above);
- OUT-1 / OUT-2 / OUT-3 write crossings (above);
- A single broker-mediated request channel for shim handles (clock,
  PRNG, budget-status) — implemented as host-side function calls or
  vsock/virtio mediated host calls per substrate; the wire format is
  governed by file `02.2.3`.

There is no executor↔executor channel. There is no executor↔sidecar
channel. There is no executor→external-network channel of any kind.

---

## 4. Forbidden surfaces (denied at the boundary)

All of the following are denied. Any executor that exhibits, attempts,
or is configured for any of them is `exited_tainted` per file
`03.6.3`, and admission of the executor class is denied or demoted
per §3.14 and `phase2_promotion_gate`.

### F-1. Network of any kind not explicitly mediated by the host

- WASI: `wasi:sockets` denied; no UDP, no TCP, no DNS.
- Apple-VM: hypervisor-level network-off (per
  `phase2_promotion_gate/02 A-ENTRY-4`).
- Sidecar: outbound only via the signed transport governed in
  `phase2_promotion_gate/02 C-ENTRY-2`; never an arbitrary egress.
- Clonefile helper: process-level network-off per §22.4.

This is unconditional. There is no "for telemetry", no "for package
fetch", no "for diagnostic upload". File `08.4`.

### F-2. Mutation of host filesystem outside the per-run ephemeral
root and the per-run write-once output area

- Any `write` / `unlink` / `rename` / `mkdir` outside the bounded
  paths is `exited_tainted` and a §22.11 taint signal.
- Includes `kernel/stores/`, the audit ledger directory, the receipts
  store, any policy file, any plugin directory, any cache the host
  treats as mutable, any user-home file.
- For clonefile helpers: a write to a clone path that the host did
  *not* declare write-once is also forbidden — the helper does not
  get to decide which clone paths it is allowed to mutate.

### F-3. Mint, modify, or delete of any authority artifact

`CapabilityToken`, `ApprovalArtifact`, `ReplayAnchor`, `Revision`,
`SnapshotRoot`, `AuditRecord`, `DriftEventRecord`, `TaintRecord`,
`ReleaseGateRecord`, `BudgetRecord` — all denied to the executor
under any condition (this is the contrapositive of file `01.1`).

### F-4. Direct write to the audit ledger or any receipt store

Even reading these from outside the host process is denied; writing
is denied without exception. The §22.10 inter-plane interface is
host-mediated only.

### F-5. Acquisition of host secrets

Environment variables, files, sockets, kernel keyrings, system
keychain, or any other source of host secret material is unreachable
from the executor. Secret-bearing capabilities are not issued by the
broker (file `02.4`).

### F-6. Executor-internal subprocess spawn that bypasses the
boundary

A subprocess spawned by the executor (where substrate permits any
spawn at all — Wasmtime/WASI does not) inherits the same boundary.
A subprocess that opens a network socket, writes outside the
ephemeral root, or otherwise crosses F-1..F-5 taints the parent
session.

### F-7. Capability re-issuance, forwarding, or aliasing

The executor may not re-export an effect handle to another executor
session, share it across a sidecar/network boundary, or alias it
into a longer-lived holder (file `02.2`, `08.10`).

### F-8. Ambient nondeterminism

Wall-clock reads outside the granted clock shim, RNG reads outside
the granted PRNG shim, hostname / TTY / locale reads, scheduling
control, real-time priority adjustments. All denied. Use of any
ambient nondeterminism source is `exited_tainted` and forces
classifier downgrade for the run regardless (file `06.2`/`06.3`).

### F-9. Self-modification of the executor's own image

The executor may not modify its own binary image, base image, engine
configuration, or any host-side cache that the host reads to
determine `environment_fingerprint`. The image is read-only.

### F-10. Effects on shared OS state

`sysctl`, kernel module load, ulimit changes, mount/unmount, swap
changes, process listing of host processes, `kill` outside the
executor's own session — all denied. (Hypervisor / WASI / sandbox
boundaries make most of these unreachable; this clause forbids any
substrate-specific workaround that re-exposes them.)

### F-11. Influence on host scheduler or budget

The executor may not request more budget, defer the reaper, extend
its own deadline, or otherwise influence host scheduling. Budget is
exposed read-only (IN-2); it is not a writeable resource (file
`02.4`).

### F-12. Influence on `replay_classifier`

The executor may not provide its own classification, suppress its
own `DriftEventRecord` emission, or signal "this run was deterministic
and you can mark exact". Classification is host-only (file `01.A-8`).

### F-13. Influence on taint graph attribution

The executor may not author `TaintRecord` (§23.17), modify a taint-
bearing input's taint state, or selectively withhold output bytes to
"clean" a tainted input. Taint graph (§22.11) attribution is host-
only.

---

## 5. Mutation surface decision matrix

| Surface | Read | Write | Why |
|---|---|---|---|
| Per-run preopened inputs | yes (IN-1) | no | §22.4 host read-only |
| Per-run write-once output area | yes | yes (OUT-1) | bounded, ephemeral, host-scrapes |
| Per-run candidate byte buffer | n/a | yes (OUT-2) | host computes digest at exit |
| Clock shim handle | yes (IN-2) | n/a | host-deterministic only |
| PRNG shim handle | yes (IN-2) | n/a | host-seeded only |
| Budget-status handle | yes (IN-2) | n/a | read-only window into host accounting |
| Subset of `environment_fingerprint` | yes (IN-3) | no | host-canonical |
| Pre-staged inputs from prior stages | yes (IN-4) | no | bounded preopens only |
| Host filesystem outside ephemeral root | no | no | F-2 |
| `kernel/stores/` | no | no | F-2, F-4 |
| Audit ledger | no | no | F-4 |
| Receipts store | no | no | F-4 |
| Capability store | no | no | F-3 |
| Policy files | no | no | F-2 |
| Network (any) | no | no | F-1 |
| Host secrets / keychain / env | no | no | F-5 |
| Other executor sessions' handles | no | no | F-7 |
| Own image / base image / engine config | no | no | F-9 |
| Shared OS state (sysctl, mount, etc.) | no | no | F-10 |
| Host scheduler / budget / reaper deadlines | no | no | F-11 |
| `replay_classifier` adjudication | no | no | F-12 |
| Taint graph attribution | no | no | F-13 |

---

## 6. The two questions a reviewer should ask of any new surface

A future proposal that suggests adding any I/O surface should be
required to answer both of:

1. **Necessity.** Is this surface required by an identified workload
   that has otherwise been admitted under
   `phase2_promotion_gate`? If not, the surface is unnecessary and
   denied under §3.13 (minimality at the hot path).
2. **Containment.** Can the surface be issued through a single broker
   effect handle that satisfies file `02.2`'s scoped/single-use/
   non-forwardable/non-introspectable/revocable properties? If not,
   the surface is uncontainable and denied under §3.1 / §3.11.

Any surface that does not satisfy both is denied. There is no third
question.

---

## 7. Net statement

The executor lives inside a **shrink-wrapped read mostly, write a
little, signal exit** envelope. Inputs are bounded and read-only;
outputs are bounded and write-once; exit is observable. Authority
artifacts, host filesystem, network, secrets, and scheduling are
unreachable. No allowed I/O surface above can be widened without a
separate design increment that re-evaluates files `01`–`06` end to
end.
