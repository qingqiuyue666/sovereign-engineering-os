# 03 — Quarantine / Execution Admission Rules

Scope: the **exact** rules the host applies before, during, and after
admitting a single executor invocation. This file is per-call, not
per-substrate; it complements (does not replace) the per-substrate
entry criteria in `phase2_promotion_gate/02_…` and the per-call
broker boundary in this package's `02_…`.

This is design only. It does not modify `validation/quarantine/*` or
any phase-1 runtime module. It pins what the seam must require so a
future implementation has an unambiguous target.

Constitutional anchors: §3.2, §22.1, §22.4, §22.6, §22.11, §23.14,
§23.17, §9.6, §9.7.

---

## 1. Pre-admission checks (executed host-side, before any executor
runs)

A single executor invocation is **admitted to run** only when *all*
of the following hold. Failure of any single check is a refusal class
defined in §3 below; refusal is the default.

### Q-1. Caller is the Python control plane

The invocation request originates from a control-plane caller that
holds the responsibility for the lane stage requesting the
invocation (validation lane, intent build, etc.). No executor may
invoke another executor, directly or transitively. Sidecar/remote
workers do not chain.

### Q-2. Capability token is present and valid

A `CapabilityToken` (§22.6, §23.13) is presented by the caller to the
broker. The token must:

- be valid under the *current* policy version;
- be scoped to this invocation's intended effect;
- be unconsumed (single-use);
- be unexpired;
- carry the lane / intent / revision identifiers needed for §22.11
  taint attribution.

Token absence = refusal class REF-CAP. Token mismatch = REF-CAP.
Token expiry = REF-CAP. Re-use = REF-CAP. Out-of-policy = REF-POL.

### Q-3. Quarantine envelope satisfies §22.4

The envelope to be handed to the executor satisfies all six §22.4
guarantees:

- **network-off** at the appropriate boundary (process-level on the
  host runner; hypervisor-level on substrate A; transport-only and
  signed for substrate C; not applicable for substrate B which has
  no socket capability at all);
- **host filesystem read-only** at every path the envelope exposes
  except the per-run ephemeral root and the per-run write-once output
  area;
- **isolated caches** — no shared mutable cache crosses sessions;
- **disposable filesystem layer** — the ephemeral root is created
  per run and reaped on exit (file `02.5`);
- **bounded resources** — CPU/RAM/disk caps from §5.2 / §5.4 are
  encoded into the envelope before exposure;
- **secret isolation** — no host secret is reachable from the
  envelope; the executor sees only the explicit effect handles the
  broker issued (file `02.2`).

Envelope failure on any guarantee = REF-Q. Silent envelope weakening
= refusal under `08.6`.

### Q-4. Effect-handle catalog is canonicalized and bound

The host computes the canonical handle catalog for this session
(file `02.2.3` W-3, W-5) and binds it as part of
`environment_fingerprint` *before* the executor is started. The
`version_tuple_hash` for the receipt this invocation contributes to
is computed host-side using the canonicalized catalog (per
`phase2_promotion_gate/02 CF-7`).

### Q-5. Replay downgrade path is wired for every dimension this
executor weakens

Per `phase2_promotion_gate/02 CF-3`, the `replay_classifier` must
already emit `DriftEventRecord`s for every dimension this specific
executor cannot satisfy (time, randomness, worker determinism, audit
binding — see file `06`). This package re-asserts: substrate
admission does not introduce the downgrade path; the downgrade path
is a precondition.

If the downgrade path is absent or unverified for a dimension this
invocation depends on, refusal class REF-DOWN.

### Q-6. Enter `AuditRecord` is composed and durable before exposure

The host *composes* the enter `AuditRecord` (executor identity,
version, base-image/engine hash, capability token id consumed,
declared time/random/scheduler shim policy, handle catalog digest,
budget envelope) and persists it to the §22.1 WAL path *before* the
executor is exposed to any handle. An executor that has been exposed
to a handle without a durable enter record is an `exited_tainted`
session by definition (file `06.4`).

### Q-7. Crash-window is classified for this executor's broker path

Per §22.1, the crash-window for the broker's issuance path is known
and tested for this executor (file `02.5.3`). Untested crash-window
behavior for the broker is a refusal under `08.13`.

### Q-8. Caller declares the demotion trigger

Per `phase2_promotion_gate/06.8`, the admission PR for this executor
class names the failure that demotes it. Per call, the *invocation*
record carries a reference to that named demotion trigger so a later
incident is matched to the pre-registered class.

---

## 2. During-execution constraints (host posture)

While an executor is running, the host:

- **Does not share** any state with the executor beyond the issued
  effect handles. There is no "side fetch" path.
- **Does not honor** any executor-originated request not made through
  a handle. Out-of-band requests (e.g., a sidecar opening a network
  socket back to the host) are treated as `exited_tainted`.
- **Does not extend** budget, deadline, or capability mid-flight. Any
  mid-flight extension is a separate, host-initiated invocation with
  its own pre-admission check (this section, run again).
- **Does not promote** any in-flight bytes from the executor into
  authority artifacts (no streaming `AuditRecord`, no streaming
  `ReplayAnchor`).
- **May reap** at any time via the broker reaper (file `02.5`); the
  executor has no veto.

---

## 3. Refusal classes

Refusal is per-invocation, named, and audit-emitting. Every refusal
class causes a host-side `AuditRecord` of the refusal with the class
identifier, the failed check id (Q-1..Q-8), and the originating
caller. No refusal is silent.

| Class | Trigger |
|---|---|
| REF-CAP | capability token absent / mismatched / expired / re-used |
| REF-POL | token present but out of current policy version |
| REF-Q | quarantine envelope fails any §22.4 guarantee |
| REF-FP | `environment_fingerprint` cannot be canonicalized for this session |
| REF-DOWN | replay downgrade path not wired for a weakened dimension |
| REF-WAL | enter `AuditRecord` could not be made durable on §22.1 path |
| REF-CRASH | broker crash-window for this executor not classified/tested |
| REF-DEMOTE | demotion trigger not named for this executor class |
| REF-SCOPE | invocation requests a non-scope effect (file `01.7`) |
| REF-CHAIN | invocation originates from another executor (Q-1) |

---

## 4. Admission outcomes (during)

When all pre-admission checks pass, the invocation is admitted to
run. The host:

- exposes the canonical effect-handle set to the executor;
- starts host-observed wall-clock and resource accounting (file
  `06.5`);
- does not begin re-validation of any output until exit signaling
  begins (no streaming admission).

---

## 5. Exit observation

Exit is observed host-side. The host records:

- exit signal (process exit code, VM exit reason, sidecar transport
  finalization, clonefile-helper exit) — *as observed by the host*;
- host-observed wall-time, CPU time, peak RSS, peak disk usage;
- bytes-returned digest (file `05.2`);
- handle catalog reaping result (every issued handle accounted for).

The executor's own claim of success or failure is recorded as
**informational evidence**, not as the exit class.

---

## 6. Exit-class adjudication (`exited_clean` / `exited_failed` /
`exited_tainted`)

Per §9.7 (quarantine run lifecycle), the host classifies exit. The
boundary rules:

### 6.1 `exited_clean`

- All handles accounted for (consumed or session-reaped).
- Exit signal indicates normal completion under host observation.
- Resource accounting within budget.
- All four binding dimensions (time, randomness, worker determinism,
  audit binding; file `06`) satisfied at the level the validator
  policy required *or* downgraded explicitly with `DriftEventRecord`
  emitted.
- Bytes-returned digest computed.
- Exit `AuditRecord` composed and durable.

### 6.2 `exited_failed`

Any one of the following:

- exit signal indicates abnormal termination, OOM, deadline,
  budget-exceedance;
- resource accounting exceeded budget without graceful return;
- handle reaping returned an unaccounted handle that is *not* taint-
  bearing (purely a liveness fault);
- transport went silent (substrate C) and the reaper could not
  positively confirm reap;
- exit signal absent within deadline.

`exited_failed` is **never** silent. Its `AuditRecord` includes the
specific failure cause and the matched refusal/failure class.

### 6.3 `exited_tainted`

Any one of the following (taint takes precedence over fail/clean):

- the executor used a handle in violation of its scope (e.g., a read-
  only fd written to via an OS-level workaround);
- the executor attempted a non-scope effect (network egress in a
  network-off envelope; subprocess in a no-subprocess executor);
- handles were exposed without a durable enter `AuditRecord` (Q-6
  violated);
- the broker reaper could not confirm reap *and* the failure mode is
  consistent with possible authority-side influence (e.g., bytes
  returned but capability accounting incoherent);
- the bytes-returned digest cannot be computed (e.g., write-once
  output area corrupted);
- the host detects a §22.11 taint signal in returned bytes that the
  executor did not declare.

### 6.4 No fourth class

There is no `exited_partial`, no `exited_clean_with_warning`, no
`exited_succeeded_for_review`. The classification is one of the
three above, and `exited_tainted` dominates `exited_failed` which
dominates `exited_clean`.

---

## 7. Post-exit handling

On exit:

- The exit `AuditRecord` is authored host-side (file `06.4`) and
  persisted on the §22.1 WAL path before any downstream stage
  consumes the invocation's outputs.
- Returned bytes are passed to ingress (file `05`) as **candidate
  material**, not as admitted artifacts. Ingress runs only after the
  exit `AuditRecord` is durable.
- The broker's reaper completes; orphaned handles trigger their own
  `AuditRecord` (R-2/R-4 in file `02.5.2`).
- The ephemeral root and write-once output area are reaped per the
  envelope's §22.4 disposable-layer guarantee.
- A `TaintRecord` (§23.17) is emitted for every taint-bearing exit
  (`exited_tainted`) and for any partially-attributable
  `exited_failed` whose unaccounted handles touched taint-bearing
  inputs.

---

## 8. Per-call audit sufficiency rule

A run of an executor is admissible into the eight-stage signable
path **only if** the host can later answer, from audit alone:

1. Which executor (id, version, image/engine hash) ran?
2. Under which policy version and capability token id?
3. With which effect-handle catalog (canonicalized digest)?
4. With which time/random/scheduler shim policy?
5. Within which budget envelope, with which observed resource use?
6. With which exit class and which evidence supported that class?
7. With which downgrade events (if any) and against which dimension?
8. With which `version_tuple_hash` contribution and which bytes-
   returned digest?

A run for which any of these is unanswerable from audit is
*non-admissible*. The boundary refuses to admit a run whose audit
sufficiency cannot be guaranteed at exit time, regardless of the
content of its outputs.
