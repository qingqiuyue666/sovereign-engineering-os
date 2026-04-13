# 02 — Execution Substrate Entry Criteria

Scope: the **exact, per-substrate** entry criteria for each execution
substrate candidate named in
`governance/design/phase2_substrate/01_execution_substrate_choices.md`:

- Substrate A — Apple `Virtualization.framework` (Darwin-native VM)
- Substrate B — Wasmtime / WASI sandbox
- Substrate C — Linux/KVM sidecar or remote worker

Each substrate has its own gate. Admitting one does not admit another.
All gates are evaluated against the phase-wide prerequisites in `01`;
those must already hold.

Constitutional anchors: §5, §5.2, §5.4, §5.5, §22.1, §22.4, §22.6,
§22.11, §27, §29.

---

## Common floor (applies to A, B, and C)

Before any substrate is admitted, all of the following must be true.
Missing any one = `defer-pending-evidence`.

- **CF-1.** Phase-wide prerequisites PR-1 through PR-10 (see `01`) are
  met.
- **CF-2.** The substrate is a *bounded executor*, never an authority
  surface. The proposed implementation must be read and explicitly
  confirmed to: issue no capabilities, mint no `ReplayAnchor`,
  write no `AuditRecord` from inside the substrate, and emit no
  `ApprovalArtifact`, `Revision`, `SnapshotRoot`, or
  `CapabilityToken`. A review that cannot confirm this textually is
  a denial.
- **CF-3.** The replay downgrade path (see
  `04_replay_determinism_audit_binding_evidence.md` §§1–4) is
  already emitting `DriftEventRecord`s for every dimension this
  substrate weakens. Substrate admission does **not** introduce the
  downgrade path; it relies on it.
- **CF-4.** The substrate's enter/exit `AuditRecord` pair is
  specified, reviewed, and test-covered with forced
  `exited_failed`/`exited_tainted` transitions *before* the
  substrate is used in any real validation lane.
- **CF-5.** A pre-registered demotion trigger is named in the
  admission PR: a specific kind of failure that, if observed, returns
  this substrate from "admitted" to "deferred-pending-evidence"
  without argument (§3.14). No demotion trigger = no admission.
- **CF-6.** No non-scope change is present in the admission PR
  (PR-8 in `01`).
- **CF-7.** `version_tuple_hash` is still computed host-side only.
  Any proposal that moves this into the substrate = automatic denial
  (§8.2, §22.5).

---

## Substrate A — Apple `Virtualization.framework`

### A-ENTRY-1. Identified workload that actually requires A

An identified validator or toolchain test that **today** cannot run
honestly inside the macOS-native quarantine path, with a concrete
failure mode documented. Example categories: requires real
`/proc`, requires Linux network namespacing, requires a deterministic
libc.

- **Evidence artifact:** a reproducible failing run of that workload
  on `runner_adapter.py` with the specific failure captured.
- **Non-admission:** "would be nicer in a VM" does not qualify.

### A-ENTRY-2. Base image build is reproducible

A documented base-image build pipeline whose output hash is
reproducible across two host machines of the same hardware class.

- **Evidence artifact:** a recorded pair of hashes from two hosts,
  matching, for the same input recipe.
- **Non-admission:** a one-host-only build is evidence of a problem,
  not of readiness.

### A-ENTRY-3. Host-side capability broker design is closed

The host-side broker that translates host-issued, single-use
capability tokens into bounded effect handles inside the guest has
a closed design: wire format, durability semantics under crash
(C22.1 / `AT-006`-class), reaper behavior.

- **Evidence artifact:** a design note addressing Q-4 from
  `phase2_substrate/07_open_questions_and_blockers.md`, plus a
  TLA+ spec per TLA-2 (see `05` in this package).
- **Non-admission:** open wire format = not admitted.

### A-ENTRY-4. Network-off is enforced at hypervisor boundary

Hypervisor-level confirmation that the guest has no network path.
Process-level assertion is not enough.

- **Evidence artifact:** a test that attempts network egress from
  inside the guest and observes hypervisor-level refusal, in
  addition to the existing process-level quarantine assertions.
- **Non-admission:** "network-off is declared at policy" without
  boundary-level proof = not admitted.

### A-ENTRY-5. Environment fingerprint binds all substrate dimensions

`ReplayAnchor.environment_fingerprint` must bind: hypervisor build
id, base-image hash, declared time/randomness shim policy, guest
kernel version, and any `preopen`-like shared-folder seed hash.

- **Evidence artifact:** test that compares receipts produced with a
  changed base-image hash and verifies the fingerprint diverges.
- **Non-admission:** silent environment drift is an §3.3 violation.

### A-ENTRY-6. Quarantine lifecycle (§9.7) re-validated for VM case

`prepared → entered → executing → exited_clean / exited_failed /
exited_tainted → preserved_for_forensics → destroyed` transitions
must work under VM semantics, including the `preserved_for_forensics`
rename-out path for a guest disk image.

- **Evidence artifact:** either TLA-4 spec (see `05`) with
  counterexample count of zero for the specified properties, or a
  test matrix covering every transition for the VM case.

### A-ENTRY-7. Crash-window classification re-validated for broker

C22.1 crash-window classification extended to the host-side broker.
The broker's crash and restart behavior must produce deterministic
classification under `wal_recovery` and `INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED`.

- **Evidence artifact:** explicit crash window list for the broker,
  with classification decisions, matching the style of the existing
  `AT-006` and `AT-018` coverage.

### A-ENTRY-8. Demotion trigger

The admission PR pre-registers: *any* observed case of the guest
successfully emitting a would-be authority artifact, *any* hypervisor
bypass of network-off, or *any* `environment_fingerprint` drift not
captured in audit = immediate demotion.

---

## Substrate B — Wasmtime / WASI

### B-ENTRY-1. First validator identified and measured

An identified validator (e.g., a schema-coherence or structured-diff
checker) where a Wasm rewrite gives either (a) a measured determinism
win, or (b) a measured ≥10× throughput win on the realistic corpus.

- **Evidence artifact:** baseline and candidate measurements on the
  same corpus at the same commit, recorded as attached data.
- **Non-admission:** aesthetic or forward-looking "Rust is faster"
  without measurement = not admitted.

### B-ENTRY-2. PRNG / clock shim canonicalization decided

Q-5 from `phase2_substrate/07_open_questions_and_blockers.md` is
closed: the PRNG algorithm class, seeding API, and draw accounting
into `environment_fingerprint` are pinned in a short design note.

- **Evidence artifact:** the design note, reviewed and referenced
  from the admission PR.
- **Non-admission:** "we'll pick a PRNG later" = not admitted.

### B-ENTRY-3. Capability surface declared and audited

The Wasmtime engine configuration is: no `random_get` grant, no
`wasi:clocks` grant, no fs grants beyond explicit preopens, no net,
no subprocess. Every non-default grant is enumerated, each tied to a
host-issued capability token.

- **Evidence artifact:** a configuration test that instantiates the
  engine and fails if any non-declared grant is present.
- **Non-admission:** any grant not enumerated in audit = not
  admitted.

### B-ENTRY-4. Floating-point / SIMD pinning

Where FP or SIMD is used, engine-level pinning (e.g., disable NaN
canonicalization differences, pin rounding mode) is specified and
bound into `environment_fingerprint`.

- **Evidence artifact:** a test that produces divergent outputs under
  changed engine FP config and shows the receipt downgrades
  accordingly.

### B-ENTRY-5. Host re-binding of returned bytes

Every byte returned from a Wasm guest is hashed host-side, recorded
in audit, and the `version_tuple_hash` is computed host-side *after*
the return. The guest never participates in authority-bytes
production.

- **Evidence artifact:** confirmed by reading the host shim; explicit
  check in review.

### B-ENTRY-6. Demotion trigger

The admission PR pre-registers: *any* Wasm guest output that gets
admitted to authority without host re-binding, *any* unannounced
grant flag appearing in engine config, or *any* FP/PRNG shape change
not reflected in `environment_fingerprint` = immediate demotion.

---

## Substrate C — Linux/KVM sidecar or remote worker

### C-ENTRY-0. Default posture is rejection

Substrate C is **presumptively not admitted** in Phase 2. It is a
Phase-3+ candidate. Admitting substrate C requires every C-ENTRY-n
below *plus* the named non-admission condition in
`06_explicit_non_admission_conditions.md` §6.2 does not apply.

### C-ENTRY-1. Local path (A+B) measured insufficient

A+B must have been tried and measured insufficient for an identified,
real workload under realistic Phase-2 load. "Insufficient" means a
budgeted lane step cannot complete under §5.2, not "would be nicer
to offload".

- **Evidence artifact:** a measured saturation record on the local
  path with the specific workload that drives sidecar demand.
- **Non-admission:** no local-path saturation record = not admitted.

### C-ENTRY-2. Signed, auditable transport designed first

A transport whose every message carries a host-issued single-use
capability token id, a `version_tuple_hash` binding, a signed payload
digest, and an explicit `exited_failed` interpretation for silence.

- **Evidence artifact:** transport design note merged before any
  wire code.
- **Non-admission:** no transport design = not admitted.

### C-ENTRY-3. Sidecar produces receipts only, not authority

The sidecar never mints `ReplayAnchor`, `ApprovalArtifact`,
`CapabilityToken`, `Revision`, or `SnapshotRoot`. It returns bounded
artifacts and bytes; the host re-validates and mints.

- **Evidence artifact:** architecture review text in the admission
  PR, explicitly confirming each forbidden artifact is not produced
  remotely.

### C-ENTRY-4. Default replay class is `semantic`, never `exact`

Per `phase2_substrate/04_replay_substrate_boundaries.md`, Substrate C
defaults to `semantic`. The classifier must already enforce this
without relying on the sidecar's self-report.

- **Evidence artifact:** a test that forces a sidecar-returned
  artifact through the classifier and verifies the class is not
  `exact` absent an explicit proof bundle.

### C-ENTRY-5. Partition behavior = `exited_failed`

Silence from the sidecar is classified as `exited_failed`, never
`exited_clean`. This is a test, not a docstring.

- **Evidence artifact:** a forced-partition test covered in the
  acceptance suite.

### C-ENTRY-6. Demotion trigger

The admission PR pre-registers: *any* sidecar self-report admitted
as exit class without host re-validation, *any* network drift not
surfaced as `DriftEventRecord`, or *any* sidecar path admitted into
`exact` replay class = immediate demotion.

### C-ENTRY-7. Scope ceiling

Even fully closed, substrate C is admitted only for the identified
workload that triggered C-ENTRY-1. Admitting C for workload X does
not admit C for workload Y; each workload passes its own C-ENTRY-1.

---

## Cross-substrate checks

- **X-1.** No admission is allowed to *weaken* any invariant
  previously satisfied by the Phase-1 baseline. A substrate that
  claims "network-off" must demonstrate it at equal or stronger
  guarantee than `runner_adapter.py` — not equal-with-caveats.
- **X-2.** No admission is allowed to broaden the eight-stage
  signable path. Substrate admissions add executor options, not
  stages.
- **X-3.** No admission is allowed to introduce a new mutation class.
  Substrates execute the same classes under different conditions.

Failure of any X-n applies across all candidates and blocks the
admission PR entirely.
