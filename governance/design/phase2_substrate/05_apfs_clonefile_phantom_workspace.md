# 05 — APFS clonefile / Phantom Workspace as a Future Substrate Layer

Question: should APFS `clonefile(2)` be admitted as a Phase-2 substrate
layer for "phantom workspaces" used by validation/quarantine and
worktree-style isolation?

Short answer: **conditionally yes, as an explicit substrate layer** —
*if and only if* its semantics are honestly bounded, it never crosses
the kernel authority surface, and disk governance (§5.4) is enforced
around it.

Constitutional anchors:
- §5 Hardware baseline (macOS / Apple Silicon)
- §5.4 Disk governance
- §5.5 Platform-specificity rule
- §22.4 Validation Quarantine Enforcement
- §27 Substrate strategy

---

## What APFS clonefile gives us

- O(1) copy-on-write clone of a file or directory tree at the
  filesystem level. No data copy at clone time; per-block divergence
  on write.
- Native to macOS / Apple Silicon (the constitutional baseline).
- Naturally pairs with disposable per-run workspaces (§22.4 "per-run
  disposable workspace must be created").

## What it does *not* give us

- Cross-host portability. A clonefile workspace exists on one
  filesystem on one machine. Replay across hosts cannot rely on it.
- Strong isolation by itself. clonefile is a copy-on-write surface,
  not a sandbox. It does not prevent network IO, secret exposure, or
  host-cache pollution. Those remain the job of the *runner*
  substrate (substrate A or B in §01).
- A guarantee that block-level CoW preserves application-level
  durability ordering. SQLite/WAL is **not** placed inside a clone;
  truth keeps using the existing WAL substrate.
- Determinism on inode numbers, timestamps, or extended attributes.
  Anything depending on those is non-admissible for exact replay.

---

## Proposed role: "phantom workspace" substrate layer

Definition: a *named* substrate layer whose only job is to provide a
disposable, content-isolated, fast-to-spawn workspace for a single
quarantine run.

### What the phantom workspace owns
- Per-run root directory, materialized via `clonefile` from a
  pre-sealed snapshot directory whose `SnapshotRoot.root_hash`
  (23.3) is bound into the validation receipt.
- Per-run cache namespace (also clonefile-backed) wired so that the
  runner cannot reach the host's shared cache.
- Teardown: a single `rm -rf` (or, where forensics is needed, a
  rename into a preserved-for-forensics location per §9.7
  `preserved_for_forensics`).

### What the phantom workspace does **not** own
- Authority. The kernel never reads truth from the phantom workspace.
  Truth remains in `kernel/stores/sqlite/` via the WAL substrate.
- Capability enforcement. The runner substrate (A or B) enforces
  that; the phantom workspace just supplies a disposable filesystem.
- Network isolation. That belongs to substrate A's hypervisor
  boundary or substrate B's WASI deny-by-default.
- Replay environment fingerprint. The phantom workspace contributes
  a hash (the source `SnapshotRoot.root_hash` plus a bounded set of
  layered-clone metadata), but not a full environment claim.

### Layering with §01 substrate choices
- Substrate A (`Virtualization.framework`): the host can clonefile
  the disk image and shared-folder seed before guest start. Inside
  the guest, the OS uses ext4/xfs; clonefile is purely a host-side
  speedup for spawning the guest.
- Substrate B (Wasmtime/WASI): clonefile-backed preopens give the
  guest a disposable, deterministic root with O(1) spawn cost.
- Substrate C (sidecar/remote): clonefile is irrelevant; the sidecar
  has its own filesystem.

---

## Required guarantees if admitted

1. **Disposability.** Every clone is destroyed on exit unless the run
   is in `exited_failed` / `exited_tainted` and policy preserves it
   for forensics (§9.7). No "ambient leftover" clones.
2. **Content provenance.** The seed snapshot's `SnapshotRoot.root_hash`
   is recorded in the validation receipt and bound to
   `version_tuple_hash`. A drifted seed is a `DriftEventRecord`.
3. **Cache isolation.** Cache namespaces are clone-backed and never
   shared across runs.
4. **Forensics path.** When a run is preserved for forensics, the
   clone is renamed into a preserved area whose retention is
   governed by the disk-governance policy (§5.4). Preservation is
   bounded, audited, and revocable.
5. **No truth crossing.** The WAL/SQLite truth substrate is **not**
   inside the clone. Authority writes never go through the phantom
   workspace.
6. **Disk-budget honesty.** Even though clones are O(1) at creation,
   per-block divergence on write can grow disk usage non-trivially
   under heavy validation churn. The phantom workspace participates
   in the §5.4 disk-governance budget.

## Failure modes to design against

- "Forgotten clones" accumulating after crashes. Design: a startup
  reaper that finds clones whose owning run is not in a live state
  and either preserves them per policy or destroys them, emitting an
  `AuditRecord`. Reaping is never silent.
- xattr / inode metadata divergence affecting builds. Design: declare
  these as *not* part of the replay environment fingerprint; any
  validator depending on them is non-admissible for exact replay.
- Filesystem pressure causing clone failures. Design: clone failure
  is a `prepared -> exited_failed` transition; never a downgrade to
  shared-host workspace.

## Promotion bar

This substrate layer is **deferred-pending-evidence**. Admission to
Phase-2 implementation requires:
- A measured cost in current Phase-1 quarantine spawn (the existing
  `runner_adapter.py` path) that exceeds budget under realistic
  validation load, *or*
- A demonstrated isolation gap that a clonefile-backed disposable
  workspace would close honestly.

Until then, this section stands as a *design-ready* substrate-layer
proposal, not an authorized component.

## Honest negative answer

If a future evaluation finds that:
- the host runs APFS volumes that don't reliably support clonefile in
  the relevant filesystem configuration, or
- clone churn under realistic load violates §5.4 disk governance
  faster than it saves spawn time,

then APFS clonefile is **not admitted** as a substrate layer and the
phantom-workspace concept is implemented via plain copy or via
substrate A's image-clone path instead. The choice is evidence-bound,
not aesthetic.
