# 01 — Exact Authority vs Non-Authority Split

Scope: the **exact inventory** of authority responsibilities that
remain in the Python control plane regardless of which external
executor is introduced, and the **exact inventory** of responsibilities
that an external executor may legally hold. Where these two
inventories meet is the boundary this package governs.

Constitutional anchors: §3.1, §3.11, §3.13, §22.1, §22.2, §22.3,
§22.5, §22.6, §22.10, §23.11, §23.12, §23.13, §23.14, §27.

This file does not introduce new responsibilities. It catalogs
existing ones and assigns each to exactly one side of the boundary.

---

## 1. The eight authority responsibilities (host-only, never move)

Each item below is an **authority surface**. By §3.1 (truth
sovereignty) and §3.11 (authority locality), each must be authored by
the Python control plane host process and may not be authored by, or
delegated to, any external executor of any substrate shape, including
APFS clonefile-backed phantom workspaces. A proposal that moves any
of these into an executor is denied automatically (`08.1`).

### A-1. Capability issuance

`CapabilityToken` (§22.6, §23.13) is *minted* by the host. An executor
**consumes** capabilities; it never mints them. A capability is
single-use and scoped per §22.6; the executor sees only the bounded
effect handle the broker translates the token into.

### A-2. Approval barrier adjudication

`ApprovalArtifact` (§22.3, §23.11) is adjudicated host-side. No
executor decides whether an approval is satisfied, sufficient,
expired, or revoked.

### A-3. Seal ordering adjudication

`SnapshotRoot` and seal ordering (§22.1, §22.2, §23.3) are adjudicated
host-side. No executor decides what is sealed, in what order, or under
what causality fence.

### A-4. `ReplayAnchor` minting

`ReplayAnchor` (§22.5, §23.12) is minted host-side, only after the
executor's exit `AuditRecord` is durable and the executor's
contributions have been re-validated host-side per file `06`. No
executor mints, modifies, or deletes any `ReplayAnchor`.

### A-5. `AuditRecord` authoring

`AuditRecord` (§22.10, §23.14) is appended to the audit ledger
host-side only. No executor writes to the ledger directly. Enter/exit
audit pairs around an executor invocation are *authored by the host*,
populated from host-observed evidence, not from the executor's
self-report (file `06.4`).

### A-6. `Revision` / `SnapshotRoot` minting

`Revision` (§23.1) and `SnapshotRoot` (§23.3) are minted host-side.
No executor produces new `Revision`s or `SnapshotRoot`s; an executor
may *consume* a `Revision` (e.g., as input bytes) under a scoped,
read-only effect handle, but never authors one.

### A-7. `signoff_gate` evaluation

The §31 sign-off gate is evaluated host-side, by the control plane,
against host-visible evidence. No executor evaluates sign-off; no
executor signals "ready to sign off"; sign-off is not influenced by
executor-internal state except through host-re-validated artifacts.

### A-8. `replay_classifier` adjudication

The classifier (§22.5, §3.12) decides the replay class
(`exact` / `diagnostic` / `semantic` / `degraded` / `unreplayable`)
and emits `DriftEventRecord`s (§23.19). It is host-only. No executor
sets a class, raises a class, or suppresses a `DriftEventRecord`. An
executor's *self-report* of "I was deterministic" is not evidence for
class assignment.

### Composition note (informational, not a ninth authority)

`version_tuple` *composition* (§8.2, §22.5) is host-only — the
**policy** of how a version tuple is composed must remain host-side.
The hash kernel itself (a pure function over canonical bytes) is a
candidate for downshift to Rust under
`phase2_substrate/03` R-1 / `phase2_promotion_gate/03 R-1`, but the
*composition policy* (which fields, in which order, with which
canonicalization rules) is not delegable to any executor. This is the
same posture as in `phase2_promotion_gate/06.1`.

---

## 2. The bounded-executor responsibility set (executor-eligible)

By contrast, the following are responsibilities a bounded external
executor *may* hold, subject to the boundary clauses in files
`02`–`06` and to per-candidate admission via
`phase2_promotion_gate`. Holding any of these does **not** make the
executor an authority surface; the host re-validates the outputs
before they enter the eight-stage signable path.

### E-1. Compute over host-supplied bytes

Pure or near-pure transformation of bytes the host hands in via
scoped, single-use effect handles. Examples: a deterministic
schema validator running in Wasmtime; a static analyzer running in an
Apple-VM Linux guest; a deterministic structured-diff coherence check
running over a clonefile-backed phantom workspace.

### E-2. Toolchain execution under quarantine

Compilation, test execution, language-runtime invocation against a
read-only or ephemeral workspace, under the §22.4 quarantine
guarantees (network-off, host read-only at the relevant path,
isolated caches, disposable filesystem layer, bounded CPU/RAM/disk,
secret isolation).

### E-3. Production of *candidate* artifacts

An executor produces *bytes* and *exit signals*. These are
**candidate material** in the §7.3 sense (file `05`); they become
admissible into the eight-stage signable path only after host-side
re-validation, schema conformance, capability reconciliation,
taint-graph intake, and replay classification.

### E-4. Honest exit signaling

An executor signals exit with a host-observable status; the host
classifies the exit as `clean`, `failed`, or `tainted` per §9.7 from
*observed* evidence. The executor's own claim of "clean exit" is
informational; the host's classification is authoritative (file
`05.5`).

### E-5. Bounded resource consumption within budget

Per-call CPU, RAM, and disk consumption inside the budget the host
issued (§5.2, §5.4, §22.6). Exceeding the budget is an exit-class
classification event, not an authority event.

### E-6. Read-only consumption of explicitly granted inputs

Read-only access to bytes the host made available through scoped
preopens / read-only mounts / shared-folder handles (file `04.2`).
The executor may not enumerate, traverse, or mutate any path the
host did not explicitly preopen.

---

## 3. The seam: who is allowed to do what to whom

The boundary admits only four classes of legitimate crossings.
Everything else is denied (§3.2 default-deny applied at the seam).

### Crossing class C-1. Host → executor: capability handoff

Host hands the executor a *bounded effect handle* derived from a
single-use `CapabilityToken`. The executor sees the handle; it does
not see the token, the issuance state, or any other capability. The
broker's behavior is specified in file `02`.

### Crossing class C-2. Host → executor: input bytes

Host exposes a bounded set of input bytes (preopens, ephemeral root,
clonefile snapshot of a path, etc.) under §22.4 quarantine
guarantees. The executor reads; it does not write back through this
crossing. Mutation surfaces are file `04.3`.

### Crossing class C-3. Executor → host: candidate output bytes

Executor returns a bounded byte buffer (or a bounded set of files in
an ephemeral path the host scrapes after exit). These are candidate
material per file `05`. The host computes a digest before any
admission decision.

### Crossing class C-4. Executor → host: exit signal and resource accounting

Executor surfaces exit code, host-observed wall-time, host-observed
CPU and RSS, and host-observed disk usage. These are evidence inputs
to the host's exit classification (`clean` / `failed` / `tainted`).

There is no fifth class. In particular there is no "executor publishes
a receipt", no "executor writes to audit", no "executor mints a
capability", no "executor decides classification", no "executor reads
arbitrary host paths", and no "executor opens its own network".

---

## 4. Authority/non-authority decision matrix

| Responsibility | Side | Constitutional anchor | Crossing class allowed |
|---|---|---|---|
| `CapabilityToken` mint | host | §22.6, §23.13 | (host-only; never crosses) |
| `CapabilityToken` consume (as effect handle) | executor | §22.6 | C-1 |
| `ApprovalArtifact` adjudication | host | §22.3, §23.11 | (host-only) |
| Seal ordering, `SnapshotRoot` mint | host | §22.1, §22.2, §23.3 | (host-only) |
| `ReplayAnchor` mint | host | §22.5, §23.12 | (host-only) |
| `AuditRecord` author/append | host | §22.10, §23.14 | (host-only) |
| `Revision` mint | host | §23.1 | (host-only) |
| `signoff_gate` evaluation | host | §31 | (host-only) |
| `replay_classifier` adjudication | host | §22.5, §3.12 | (host-only) |
| `version_tuple` composition policy | host | §8.2, §22.5 | (host-only) |
| `version_tuple` hash-kernel pure function | host (R-1 candidate) | §8.2 | (host-only; downshift candidate) |
| Compute over supplied bytes | executor | §22.4 | C-1, C-2, C-3 |
| Toolchain execution under quarantine | executor | §22.4 | C-1, C-2, C-3, C-4 |
| Candidate-artifact production | executor | §7.3 | C-3 |
| Exit signal / resource accounting | executor | §9.7 | C-4 |
| Read of explicitly granted inputs | executor | §22.4 | C-2 |
| Network egress | neither (denied at boundary; file `04.4`) | §22.4 | (none) |
| Mutation of host filesystem outside ephemeral root | neither (denied) | §22.4, §22.8 | (none) |
| Capability re-issuance / forwarding | neither (denied) | §22.6 | (none) |
| Audit-ledger writes from inside executor | neither (denied) | §22.10 | (none) |

---

## 5. Why APFS clonefile-backed phantom workspaces are still bounded executors

A clonefile-backed phantom workspace lives on the host's own
filesystem; its proximity to authority surfaces makes the boundary
*more* important, not less. Such a helper:

- runs as a bounded executor in this package's sense;
- is granted only a scoped, ephemeral path under §22.4;
- may not enumerate or mutate any path other than its own clone;
- may not write to `kernel/stores/`, the audit ledger, or any
  capability or receipt store;
- contributes only candidate material per file `05`;
- contributes audit/replay evidence per file `06` exactly as a VM
  guest or sidecar does.

The fact that the helper happens to share an inode-storage substrate
with the host is irrelevant to its authority status. It has none.

---

## 6. Edge cases explicitly resolved

- **"The executor needs to log."** Executor logs are *bytes*. They
  return through C-3 as candidate material; the host decides whether
  any of them are kept, classified, redacted, or referenced. The
  executor does not write to the audit ledger.
- **"The executor needs a clock for timestamps."** Wall clock inside
  any executor is untrusted (per `phase2_substrate/04 §1`). The host
  brackets the executor with host-observed enter/exit timestamps;
  any in-executor clock must come from a host-deterministic clock
  shim, recorded in `environment_fingerprint`, or the receipt is
  downgraded.
- **"The executor needs randomness."** Same as time: host-issued PRNG
  only, recorded in `environment_fingerprint`. No `/dev/urandom`.
- **"The executor needs to spawn subprocesses."** Permitted only
  inside the executor's own bounded compute envelope; spawned
  subprocesses inherit the same boundary (no audit, no capability
  mint, no host-fs mutation outside ephemeral root). Wasmtime/WASI
  guests do not get subprocess capability under any circumstance
  (file `08.4`).
- **"The executor needs to call back into the host for help."**
  Permitted only through the broker's bounded effect handles
  (file `02`). The executor cannot synthesize new requests, only
  consume the handles it was given at admission.
- **"The executor needs to update a cache."** Caches that affect
  truth (e.g., `version_tuple`-keyed result caches) are host-owned;
  executor-internal caches are host-disposed at exit. No cache write
  crosses C-3 except as candidate bytes the host re-validates.

---

## 7. Net statement

There are exactly two roles at this seam: the **single Python
control-plane authority** and a **bounded, capability-gated,
audit-bracketed, replay-classified consumer** that the host treats as
a worker per §29. Any attempt — by design, by accident, by adjacent
configuration, or by future "convenience" feature — to introduce a
third role is denied automatically (`08.1`, `08.11`).
