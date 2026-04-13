# 02 — Host/Guest Capability-Broker Boundary

Scope: the **exact** boundary between the host-side capability broker
and any external executor (Wasmtime/WASI guest, Apple-VM Linux guest,
Linux/KVM sidecar or remote worker, APFS clonefile-backed phantom
workspace helper). This file says what the broker is, what it issues,
what it never issues, what it reaps, and how it behaves under crash
and timeout.

This is design only. No broker code is introduced here. The Q-4
open-question carrier (`phase2_substrate/07 §Q-4`) remains open at
implementation level; this file pins the *boundary shape* so that any
future implementation of the broker has an unambiguous target.

Constitutional anchors: §3.1, §3.11, §22.1, §22.6, §22.10, §23.13,
§23.14.

---

## 1. What the broker is

The capability broker is a **host-side, in-process component of the
Python control plane** that translates host-issued, single-use
`CapabilityToken`s (§22.6, §23.13) into bounded, scoped **effect
handles** that an executor can use, then reaps those handles
deterministically.

It is the *only* mechanism by which an executor can perform an effect
that requires authority. There is no second mechanism. There is no
"side channel". There is no "implicit grant by file presence".

The broker does **not**:

- run inside any executor;
- live in a sidecar;
- mint `CapabilityToken`s (host control-plane code mints; the broker
  *consumes* the token and *issues* the corresponding handle);
- author `AuditRecord`s (the broker records evidence the host audit
  layer authors);
- decide policy (the broker enforces policy decided host-side);
- maintain its own truth (the broker is stateless across runs except
  for an in-memory effect-handle table the reaper governs).

---

## 2. Boundary primitives

### 2.1 `CapabilityToken` (host-internal, never crosses)

Defined in §23.13 already. The broker's relationship to the token:

- The token is presented to the broker by host control-plane code,
  not by the executor.
- The broker validates the token against the policy version recorded
  in the token, scope, expiry, and single-use status.
- On validation, the broker produces an **effect handle** (see 2.2)
  and records the consumption host-side. The token is *spent* at this
  point, regardless of whether the executor ever uses the handle.
- The token itself **does not cross the host/executor boundary**. The
  executor never sees the token id, the issuance state, the policy
  version field, or any other capability.

### 2.2 Effect handle (the only thing the executor ever sees)

An **effect handle** is a bounded, scoped, single-use reference to one
specific permitted effect. Examples (illustrative; concrete catalog is
out of scope for this design package):

- a read-only file descriptor for a single preopened directory;
- a read-only file descriptor for a single named input artifact;
- a write-once file descriptor for a single byte buffer in the
  executor's ephemeral output area (the host scrapes after exit);
- a clock-shim handle that returns the host-deterministic clock value
  the policy authorizes (and only that);
- a PRNG-shim handle that returns bytes from the host-seeded PRNG
  recorded in `environment_fingerprint`;
- a budget-status handle that returns the remaining CPU/RAM/disk
  budget for this run.

Properties (every executor, every effect handle):

- **Scoped.** Refers to exactly one effect; cannot be widened by the
  executor (e.g., a read-only fd for `/inputs/x` cannot be
  re-`open()`ed for `/inputs/y`).
- **Single-use or single-session.** Either consumed once and reaped,
  or pinned to the executor session and reaped at session exit.
- **Non-forwardable.** The executor may not re-export, share with a
  spawned subprocess across a sidecar/network boundary, or otherwise
  alias the handle into a separate executor session.
- **Non-introspectable.** The executor cannot read out the underlying
  token id, the policy version, or any host-internal identifier from
  the handle.
- **Revocable.** The host (via the reaper, see §5) may invalidate the
  handle at any time without cooperation from the executor.

### 2.3 Wire format requirements (boundary-shape only)

This package does not pin a concrete wire format (Q-4 in
`phase2_substrate/07`). It does pin what the wire format must
guarantee:

- **W-1.** The wire format is host-defined, not guest-influenced.
- **W-2.** The wire format does not embed `CapabilityToken` fields;
  it embeds only effect-handle identifiers opaque to the executor.
- **W-3.** The wire format is canonicalizable to bytes (so that
  `environment_fingerprint` can record the exact handle catalog made
  available, host-side).
- **W-4.** The wire format is single-direction per call: a host→
  executor grant is one direction, an executor→host result is the
  other; there is no in-band capability synthesis by the executor.
- **W-5.** The wire format admits a deterministic enumeration that
  the host can replay, so that "which handles were exposed in run R"
  is part of the audit record (file `06.1`).

A future implementation that does not satisfy W-1 through W-5 is not
admissible regardless of how many tests it has.

---

## 3. What the broker may issue

Only effect handles whose underlying `CapabilityToken` is:

- valid under the current policy version;
- scoped to this single executor session;
- single-use (or session-scoped with a reaper deadline);
- audit-bracketed by a paired enter/exit `AuditRecord` host-side.

Every issued handle is **logged** as broker evidence, which the host
audit layer authors into `AuditRecord` (§22.10). The handle catalog
for a session is part of `environment_fingerprint` and is bound into
the eventual `ReplayAnchor` (file `06`).

---

## 4. What the broker never issues

Regardless of executor, substrate, or workload, the broker may not
issue:

- A handle that allows an executor to mint `CapabilityToken`,
  `ReplayAnchor`, `ApprovalArtifact`, `Revision`, `SnapshotRoot`,
  `AuditRecord`, or `DriftEventRecord` — these are A-1 through A-8 in
  file `01` and are denied at the boundary.
- A handle that allows an executor to write to the audit ledger,
  the receipts store, the capability store, or any other authority
  store under `kernel/stores/`.
- A handle that allows an executor to open arbitrary network sockets,
  resolve arbitrary DNS, or originate any unsolicited network egress
  (file `04.4`).
- A handle that allows an executor to enumerate the host filesystem
  outside the ephemeral root and the explicitly preopened paths.
- A handle that grants ambient `/dev/urandom`, ambient wall clock,
  ambient hostname, or any other un-shimmed nondeterminism source
  (file `06.2`, `06.3`).
- A handle that re-issues, forwards, or extends another handle held
  by a different executor session.
- A handle that allows the executor to query "what other handles
  exist in this session" beyond the host-canonicalized catalog the
  host already exposed at session start.
- A handle that allows the executor to extend its own budget,
  request more time, or defer the reaper.
- A handle that allows the executor to influence its own exit
  classification (the executor may signal an intended exit; the host
  classifies — file `05.5`).
- A handle that allows the executor to claim, read, or modify a
  different executor session's effect handles.

Any future capability proposal that requires one of the above to be
"sometimes" allowed is a denial under `08.1` and `08.11`.

---

## 5. Reaper behavior

A **reaper** is a host-side component (logically part of the broker)
that ensures every issued effect handle is invalidated by a known
event. The reaper is design-only here; this section pins required
behavior.

### 5.1 Triggering events

A handle is reaped on the *first* of:

- single-use consumption (for single-use handles);
- explicit executor-session exit (whether `clean`, `failed`, or
  `tainted`);
- session deadline expiry (timeout per §22.6);
- reaper sweep on detection of an orphaned session (e.g., guest crash
  with no exit signal);
- host control-plane shutdown.

### 5.2 Reaper invariants

- **R-1.** No handle persists across executor sessions.
- **R-2.** No handle persists across host control-plane restarts.
  The crash-window classification under §22.1 is *required* to cover
  the broker's effect-handle table; an unreaped handle after recovery
  is itself an `AuditRecord` event.
- **R-3.** A reaped handle that is later "used" by stale executor
  state is denied with a host-classified `tainted` exit signal for
  that session.
- **R-4.** A handle that the reaper cannot positively confirm reaped
  (e.g., a sidecar that went silent) is recorded as `exited_failed`
  (and possibly `exited_tainted` per file `03.6`), not as
  `exited_clean`.

### 5.3 Crash-window obligations

The broker is on the §22.1 WAL durability path for the *issuance*
record (the host-side audit/handle table), not for any executor-
internal state. Concretely:

- The broker logs effect-handle issuance to a host-side journal
  before the handle is exposed to the executor.
- On host crash, recovery enumerates outstanding handles and reaps
  them; sessions whose handles cannot be deterministically reaped are
  classified as `exited_failed`/`exited_tainted` per `phase2_substrate/04`
  and `06.4` here.
- This obligation applies equally to clonefile-backed phantom
  workspaces: the workspace's effect handles (read-only mount of the
  clone, write-once output area) participate in the same WAL
  discipline.

### 5.4 What the reaper never does

- The reaper does not "renew" handles.
- The reaper does not "extend" handles.
- The reaper does not "trust" the executor's report of completion;
  reap is on host-observed evidence (exit signal, deadline, sweep).
- The reaper does not write authority artifacts; it surfaces evidence
  the host audit layer authors.

---

## 6. Per-substrate boundary instantiation (boundary view, not
implementation)

This package does not specify how the wire is implemented; it
specifies what the wire must guarantee on each substrate.

### 6.1 Wasmtime / WASI

- Effect handles map to a curated subset of WASI preopens, plus host-
  shim functions exposed via WASI `imports`.
- WASI's `wasi:filesystem` is restricted to the curated preopen set;
  no `wasi:filesystem/types/Descriptor.open-at` outside it.
- `wasi:clocks` and `wasi:random/random.get-random-bytes` are denied
  unless an explicit shim handle is granted (file `06.2`, `06.3`).
- `wasi:sockets` is denied (file `04.4`, `08.4`).

### 6.2 Apple `Virtualization.framework` Linux guest

- Effect handles map to host-side broker calls bridged into the guest
  via a single, host-defined mechanism (e.g., a controlled vsock
  channel or virtio-fs preopens). The mechanism's wire format is the
  one that must satisfy W-1..W-5.
- Network is off at the hypervisor boundary (already required by
  `phase2_promotion_gate/02 A-ENTRY-4`); no broker handle is allowed
  to re-enable it in any form.
- Guest crashes are reaped by host-side teardown of the VM and its
  ephemeral disk; the broker treats unreaped sessions as
  `exited_failed`.

### 6.3 Linux/KVM sidecar or remote worker

- Effect handles cross a signed transport (per `phase2_promotion_gate/
  02 C-ENTRY-2`); the transport's payloads are opaque to the executor
  beyond the bounded handle set.
- Network silence from the sidecar is reaped as `exited_failed` (file
  `03.6`); never `exited_clean`.
- Remote worker handles are non-forwardable across remote workers
  (`02.2 W-2`/`5.2 R-1`).

### 6.4 APFS clonefile-backed phantom workspace helper

- Effect handles map to a single read-only fd for the clone root and
  a single write-once fd for the per-run output area.
- The helper is a process under §22.4 quarantine; it has no broker
  call beyond what the host pre-exposed at session start.
- The reaper deletes the clone tree on session exit; orphaned clones
  are reaped on host startup, with a host-side audit event for each.

---

## 7. Boundary clauses summary (broker-direction matrix)

| Clause | Direction | Meaning |
|---|---|---|
| BROK-1 | host→broker | host-control-plane mints `CapabilityToken`s; broker only consumes them |
| BROK-2 | broker→executor | broker exposes only opaque, scoped, single-use/session effect handles |
| BROK-3 | executor→broker | executor consumes handles; cannot synthesize new ones |
| BROK-4 | broker→host audit | broker emits issuance + consumption evidence host-side; host audit authors `AuditRecord` |
| BROK-5 | broker→reaper | every handle has a known reap event; orphans → `exited_failed`/`exited_tainted` |
| BROK-6 | broker↔WAL | issuance is on the §22.1 WAL path; recovery reaps outstanding handles |
| BROK-7 | broker→`environment_fingerprint` | the canonical handle catalog for a session is bound into the receipt; `version_tuple_hash` is computed host-side using this catalog |

A proposed broker implementation that cannot satisfy BROK-1 through
BROK-7 is denied under §3.1 and §3.11 and is not eligible for
admission under `phase2_promotion_gate` regardless of substrate
evidence.
