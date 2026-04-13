# 03 — Rust Downshift Entry Criteria

Scope: the **exact, per-candidate** entry criteria for each Rust
downshift candidate named in
`governance/design/phase2_substrate/03_rust_downshift_candidates.md`:

- **R-1** `version_tuple` hash kernel (Tier-1)
- **R-2** schema validator core (Tier-1)
- **R-3** WAL frame parser / checksum / dirty-tail classifier (Tier-1)
- **R-4** append-only ledger writer, frame layer only (Tier-1)
- **R-5** diff coherence kernel for `patch_proposal_service` (Tier-2)
- **R-6** replay anchor canonicalizer (Tier-2)

Each candidate has its own gate. Admitting one does not admit another.
All gates are evaluated against the phase-wide prerequisites in `01`
and the integration discipline in the substrate design package.

Constitutional anchors: §3.13, §3.14, §27, §28, §31.

---

## Common floor (applies to all Rust downshift candidates)

- **CF-R-1.** Phase-wide prerequisites PR-1 through PR-10 (`01`) hold.
- **CF-R-2.** The Rust component is **substrate**, not authority. It
  returns typed values; it never issues capabilities, never mints
  replay anchors, never writes to the audit ledger directly.
  A proposal that puts authority in Rust = automatic denial.
- **CF-R-3.** A/B differential harness exists **before** any Rust
  code ships. The harness drives both the Python reference and the
  Rust candidate on the same corpus and fails on any disagreement
  per the candidate's comparison mode (byte-for-byte for R-1, R-2,
  R-6; classification-equivalent for R-3, R-4).
- **CF-R-4.** The Python implementation is the **reference** until
  a failure reverses that relationship under §3.14. Any A/B
  disagreement is, by default, a failure of the Rust port.
- **CF-R-5.** Python wrapper re-checks pre/post-conditions against
  the same schema set every Rust call. No un-wrapped call path.
- **CF-R-6.** Pre-registered demotion trigger: the specific kind of
  measured or observed failure that would return the candidate to
  "deferred-pending-evidence" without argument.
- **CF-R-7.** No candidate admission broadens scope (no new language
  to the build, no new crate family beyond the one declared for
  the candidate, no repo-wide tooling changes bundled with the
  port).
- **CF-R-8.** A written port plan exists, covering the AT/INV set
  the module currently satisfies and how each is preserved.

A candidate missing any CF-R-n = `defer-pending-evidence`.

---

## R-1. `version_tuple` hash kernel

### R1-ENTRY-1. Measured drift risk or measured hot path

Either a recorded cross-interpreter divergence incident in the
current Python implementation (measured, reproducible), **or** a
measured per-artifact hash cost that exceeds a budget threshold
under realistic Phase-2 evidence-closure load.

- **Evidence artifact:** the recorded drift record or the
  measurement file against the Phase-1 baseline (PR-6).
- **Non-admission:** aesthetic "Rust is faster" without a recorded
  measurement = not admitted.

### R1-ENTRY-2. Composition policy stays Python

Only the hash kernel (canonical bytes → digest) moves. The
composition of which fields in what order remains in Python
(`kernel/version/version_tuple.py` composition logic, per
`phase2_substrate/02`). A proposal that moves composition into Rust
= automatic denial.

### R1-ENTRY-3. Byte-for-byte A/B for N runs

The A/B harness shows byte-identical digests across the full Phase-1
and Phase-2 corpus for N consecutive CI runs (N named in the
admission PR, not less than 10) before any Python path is removed.

### R1-ENTRY-4. Demotion trigger

Any A/B disagreement, any cross-host digest drift on the same input,
or any measurement showing the Rust kernel is *not* faster and *not*
more deterministic than Python = demotion.

---

## R-2. Schema validator core

### R2-ENTRY-1. Measured cost exceeds per-stage budget

A per-stage schema-validation cost measurement that exceeds the
Phase-2 budget under realistic load with the *full* schema pack.

- **Evidence artifact:** baseline measurement file (PR-6) plus a
  candidate measurement on the same corpus at the same commit.
- **Non-admission:** a cost measured only on a truncated schema pack
  or a non-representative corpus = not admitted.

### R2-ENTRY-2. Error-message stability

Validator error messages that reviewers depend on are preserved to a
snapshot-test level of stability. A Rust engine that "is faster but
returns different error shapes" forces reviewer re-training and fails
this criterion.

- **Evidence artifact:** snapshot tests for the existing error
  message shapes under the candidate engine.

### R2-ENTRY-3. Schema content stays governance

Schema files under `kernel/schemas/*.schema.json` are untouched by
this admission. Only the validator *engine* changes.

### R2-ENTRY-4. Demotion trigger

Any validation result divergence on the A/B harness, any error
message shape change that breaks review snapshot tests, or any
engine configuration drift not bound into `environment_fingerprint`
= demotion.

---

## R-3. WAL frame parser / checksum / dirty-tail classifier

### R3-ENTRY-1. Phase-wide PR-5 is closed

WAL recovery classification is stable on `main` (PR-5 in `01`).

### R3-ENTRY-2. TLA-3 spec admitted

The TLA+ spec for WAL durability and seal transaction ordering
(TLA-3, see `05`) is written and its counterexample count is zero
for the stated properties, **before** R-3 is admitted.

- **Evidence artifact:** the spec file under the future
  `governance/design/phase2_substrate/tla/` path, with a recorded
  model-check result.
- **Non-admission:** R-3 admitted without TLA-3 = not admitted.

### R3-ENTRY-3. Extended fuzz corpus pre-established

A fuzzing corpus that exercises dirty-tail and mid-segment-corruption
cases at a scale beyond current Python tests exists and fails neither
implementation before R-3 is admitted.

- **Evidence artifact:** the corpus plus its run record.

### R3-ENTRY-4. Classification A/B, not byte-for-byte

R-3 is parser + classifier. The A/B harness compares classification
outcomes per crash window, not byte-for-byte internals.

- **Evidence artifact:** the classification table with Python and
  Rust columns, identical across the corpus.

### R3-ENTRY-5. Demotion trigger

Any classification disagreement on the A/B harness, any observed
crash window that produces a classification outside the existing
legal set, or any mid-segment corruption that is not halted = demotion.

---

## R-4. Append-only ledger writer (frame layer only)

### R4-ENTRY-1. Measured writer-side saturation

A measured writer-side cost under simultaneous lane load that exceeds
the §5.2 budget. Without this measurement, R-4 is not a real
candidate; the baseline is SQLite-bound, not interpreter-bound.

- **Evidence artifact:** the measurement file (PR-6) explicitly
  attributing the saturating cost to interpreter-side framing, not to
  storage-side flush.
- **Non-admission:** storage-bound saturation does not justify R-4;
  that is a storage, not interpreter, decision.

### R4-ENTRY-2. SQLite remains the substrate

R-4 produces framed bytes and hands them to SQLite. SQLite is not
replaced or bypassed. A proposal that writes directly to disk =
automatic denial.

### R4-ENTRY-3. Append ordering preserved

The §22.2 nine-step ordering routine is preserved. Any re-ordering
for throughput that changes the semantics = denial.

### R4-ENTRY-4. Demotion trigger

Any missing frame, any duplicate frame, any ordering anomaly on the
A/B harness, or any checksum failure observed once in production =
demotion.

---

## R-5. Diff coherence kernel for `patch_proposal_service`

### R5-ENTRY-1. Patch class has broadened past Phase-1 scope

R-5 is **deferred-pending-evidence** until the patch class broadens
past Phase-1's single-file text substitution, per §28 hardening order
item 4. Before that broadening, R-5 is not admissible regardless of
other criteria.

- **Evidence artifact:** the delta-register entry that admits a
  broader patch class, merged on `main`.

### R5-ENTRY-2. Measured hot path

Once patch class has broadened, R-5 needs a measured per-call cost
that exceeds budget on the broadened patch corpus.

### R5-ENTRY-3. Byte-for-byte A/B

Structural diff is a pure function; the A/B harness runs
byte-for-byte.

### R5-ENTRY-4. Demotion trigger

Any diff disagreement on the A/B harness = demotion.

---

## R-6. Replay anchor canonicalizer

### R6-ENTRY-1. A single observed canonicalization drift

One recorded canonicalization drift incident is sufficient to admit
R-6 under §3.14.

- **Evidence artifact:** the drift record referencing specific inputs
  and divergent outputs from adjacent Python serializers.
- **Non-admission:** no recorded drift = not admitted. R-6 is
  forbidden from being admitted on "future-proofing" grounds.

### R6-ENTRY-2. Canonicalizer kernel only

R-6 moves only the canonical-bytes production. `ReplayAnchor`
content policy (which fields, validity rules) stays Python per
`phase2_substrate/02`.

### R6-ENTRY-3. Byte-for-byte A/B

Same posture as R-1. Byte-for-byte agreement on the corpus for N
consecutive CI runs before Python removal.

### R6-ENTRY-4. Demotion trigger

Any byte disagreement on the A/B harness, or any cross-host
divergence = demotion.

---

## What this section does not do

- It does not start a Rust workspace.
- It does not select crates or a build system.
- It does not admit any candidate by virtue of listing it.
- It does not shorten or batch the A/B harness requirement.
- It does not authorize removal of any Python reference
  implementation; removal is a second gate after the A/B period
  closes green.
