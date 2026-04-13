# 03 — First Candidates for Rust Downshift

Scope: identify the **smallest, highest-justification** modules to
consider rewriting in Rust during Phase-2 hardening. This is a
candidate list, not an authorization. Each candidate is qualified by
the evidence bar required to admit a port under §27 and §3.14.

Selection criteria (a candidate must score on at least two):
1. Pure, narrow, well-typed surface (low blast radius on rewrite).
2. CPU-bound under realistic Phase-2 load (not currently bottlenecked
   on SQLite or LLM I/O).
3. Determinism gains from leaving Python (e.g., explicit FP / hashing
   / canonical-bytes discipline).
4. Embeddable from Python via FFI (`PyO3` / `cffi`) or shippable as a
   `.wasm` module that runs inside substrate B (§01).
5. Has a clean, schema-bound boundary so the port can be A/B compared
   against the Python implementation byte-for-byte.

## Tier-1 candidates (most defensible to downshift first)

### R-1. `version_tuple` hash kernel
- Surface: deterministic canonical-bytes composition + cryptographic
  hash for `version_tuple_hash`.
- Why: pure function, called by every artifact-producing service,
  must be byte-identical across hosts. A tiny Rust crate eliminates
  per-interpreter ambiguity (e.g., dict ordering, string
  normalization edge cases).
- Boundary: input = canonicalized field tuple (already required by
  §8.2); output = fixed-width digest. No state.
- Evidence bar: cross-version reproducibility test corpus must show a
  measured drift risk in the Python implementation, *or* a measured
  hot-path cost during evidence closure under realistic load.
- Note: the *composition policy* (which fields, in what order)
  remains Python (`02`); only the hash kernel itself moves.

### R-2. Schema validator core
- Surface: JSON Schema evaluation for `kernel/schemas/*.schema.json`.
- Why: hot path on every artifact ingress + pre-persist. Today
  validated via `kernel/schemas/validator.py`. Rust libraries
  (e.g., `jsonschema-rs`) are an order of magnitude faster, with
  tighter error semantics.
- Boundary: schema bytes + artifact bytes → validation receipt.
- Evidence bar: a measured per-stage validation cost that exceeds the
  budget under Phase-2 load with the full schema pack.
- Note: schema *content* is governance; validator engine is
  substrate. Engine swap must keep error messages stable enough for
  reviewers (snapshot tests).

### R-3. WAL frame parser / checksum / dirty-tail classifier
- Surface: low-level read of WAL frames for the `wal_recovery`
  classifier (§22.1). Pure parser + checksum + state machine.
- Why: correctness-critical, byte-bound, deterministic. A Rust core
  is easier to fuzz and easier to model alongside §06 TLA+ work.
- Boundary: bytes in → classification record out; never writes.
- Evidence bar: extended fuzzing corpus that exercises dirty-tail
  and mid-segment-corruption cases at scale beyond what the current
  Python tests cover.

### R-4. Append-only ledger writer (frame layer only)
- Surface: serialize an `AuditRecord`/`JournalEntry` to its
  on-disk frame, compute checksum, hand to SQLite. Pure framing.
- Why: write throughput on evidence closure is a likely Phase-2 hot
  spot. Today bounded by Python interpreter cost per row.
- Boundary: typed record → bytes; SQLite is still the substrate.
- Evidence bar: measured writer-side cost under simultaneous lane
  load that exceeds budget (§5.2).

## Tier-2 candidates (worth considering, lower priority)

### R-5. Diff coherence kernel for `patch_proposal_service`
- Surface: structural diff + minimal coherence check (single-file
  text substitution today; multi-file later under §22.13).
- Why: pure function, deterministic, eventual hot path as patch
  classes broaden.
- Evidence bar: deferred until patch class broadens past Phase-1
  scope; gated by §28 hardening order item 4.

### R-6. Replay anchor canonicalizer
- Surface: produce the canonical bytes of `ReplayAnchor` (23.12)
  before hashing.
- Why: deterministic byte production deserves the same discipline
  as R-1; today shares Python serializers with adjacent code.
- Evidence bar: a single observed canonicalization drift incident
  is sufficient to admit it under §3.14.

## Explicit non-candidates for Phase 2

- `signable_path_orchestrator` — see `02`.
- `signoff_gate` — see `02`.
- `barrier_rules`, `quarantine_rules`, `capability_rules`,
  `seal_ordering`, `replay_classifier` — authority surfaces; legibility
  dominates.
- Anything UI / shell / dashboard adjacent — out of scope per
  README non-scope.

## Integration discipline (for any admitted candidate)

1. The Rust component is shipped as a *substrate*, not an authority.
   It returns typed results; the Python control plane decides.
2. Every Rust call is wrapped by a Python guard that re-checks
   pre/post-conditions against the same schema set.
3. A/B differential tests run during Phase-2 hardening: Python and
   Rust implementations must agree byte-for-byte on the corpus
   (R-1, R-2, R-6) or on classification (R-3, R-4) for a gated
   period before the Python path is removed.
4. A failed agreement is **always** treated as a failure of the
   Rust port, not of Python — the Python implementation is the
   reference until evidence reverses the relationship under §3.14.
5. No Rust component issues capabilities, mints replay anchors as
   authority artifacts, or writes to the audit ledger directly.

## What this section does not do

- It does not start a Rust workspace.
- It does not pin a crate set or a build system.
- It does not add Rust to repository tooling.
- All of the above are Phase-3 internalization decisions and remain
  deferred-pending-evidence.
