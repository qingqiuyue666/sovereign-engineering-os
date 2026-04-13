# 05 — Result Ingress Rules

Scope: the **exact** rules under which bytes returned by an external
executor become anything more than bytes. This file separates
*candidate material* from *admitted truth* and pins the reject /
downgrade / defer matrix the host applies on ingress.

This file does not change `ValidationReceipt`, `ReplayAnchor`,
`DriftEventRecord`, or any other receipt shape. It pins the *use* of
those existing fields on the ingress path.

Constitutional anchors: §3.2, §3.3, §3.12, §7.3, §7.5, §22.4, §22.5,
§22.10, §22.11, §23.7, §23.12, §23.15, §23.17, §23.19.

---

## 1. The candidate / admitted distinction

By §7.3 (artifact conversion rule), an artifact has a class. Bytes
that an executor returns are **candidate material**: they have a
host-computed digest, they are bound to the executor session that
produced them via audit, and they are subject to host-side re-
validation. They are not, and cannot become, authority artifacts
without traversing the rules below.

Concretely:

- **Candidate material** has at most: bytes, digest,
  producer-session reference, `environment_fingerprint` digest from
  the producing session, an exit class, and a per-dimension downgrade
  vector. It is *not* an authority artifact.
- **Admitted truth** is the artifact a downstream stage may read as
  if the kernel itself produced it: a `ValidationReceipt` (§23.7), a
  `BuildReceipt` (§23.8), a `SemanticReceipt` (§23.9) — with the
  receipt's `version_tuple_hash` composed host-side, the receipt's
  class adjudicated host-side, and the receipt's
  `ReplayAnchor` (§23.12) minted host-side.

A bytes object can be **only one** of:

- candidate material awaiting ingress;
- admitted truth (host-re-validated, classified, audit-bracketed);
- rejected and discarded with an `AuditRecord` of rejection;
- downgraded and admitted at a lower replay class with a
  `DriftEventRecord`;
- deferred (held as candidate, no admission, named blocker).

There is no sixth state. There is no "in-band promotion".

---

## 2. The ingress pipeline (host-side, single-threaded per session)

Every executor session's bytes traverse the ingress pipeline in
order. Failure at any gate routes to reject / downgrade / defer per
§5–7.

### Gate G-1. Exit precondition

`AuditRecord(exit)` for the producing session exists and is durable
on the §22.1 WAL path. Without G-1, no ingress runs.

### Gate G-2. Bytes-returned digest computed

The host computes a digest over the bytes-returned (OUT-1 + OUT-2
contents) before any structural parsing. The digest is bound into
the exit `AuditRecord` retroactively only to the extent the §22.1
write protocol allows (i.e., as part of the durable enter-exit
record set), never silently after-the-fact.

### Gate G-3. Capability reconciliation

Every effect handle the broker issued is matched against either
"consumed and reaped" or "session-reaped at exit". Unaccounted
handles or capability-coherence mismatches → reject under R-CAP
(§5.1).

### Gate G-4. Schema conformance

Where the candidate material is supposed to be a structured artifact
(e.g., a validator's structured-diff coherence report per §22.13),
the host parses against the existing frozen schema (§23.x). Schema
nonconformance → reject under R-SCHEMA.

### Gate G-5. Taint-graph intake

Per §22.11, every input bound into the producing session that bore
taint propagates to the candidate material. `TaintRecord` (§23.17)
is composed host-side. A taint signal on returned bytes that the
executor did not declare, but the host detects, → `exited_tainted`
classification (file `03.6.3`) and rejection (R-TAINT) of the
candidate as truth, though the `TaintRecord` itself is admitted.

### Gate G-6. Replay-class adjudication

`replay_classifier` (§22.5) computes the class for the candidate
based on the four-dimension evidence (file `06.1`–`06.4`). If any
dimension is short of the validator's required class, the classifier
*downgrades* explicitly (§3.12) and emits a `DriftEventRecord`
(§23.19). Silent class hold or silent class raise → boundary
violation (file `08.5`).

### Gate G-7. `version_tuple_hash` composition

Composition policy is host-only (file `01 §A composition note`).
The host composes the `version_tuple_hash` over (input version
tuples ∪ executor identity ∪ engine/image hash ∪ shim policy ∪
canonical handle catalog ∪ candidate digest). Composition failure
(e.g., a missing input fingerprint) → defer under D-COMPOSE (§5.7).

### Gate G-8. Receipt minting (admitted-truth construction)

Only after G-1..G-7 all pass at the validator's required class does
the host *mint* the corresponding receipt and `ReplayAnchor`. At
this point the bytes have crossed from candidate to admitted truth.

### Gate G-9. Audit closure

The host appends the ingress audit record (executor session, gate
outcomes, ingress decision, downgrade vector if any, taint vector
if any) on the §22.10 path. Without G-9, the ingress is treated as
incomplete and the candidate is held in `defer` until G-9 completes.

---

## 3. Reject rules (R-*)

A reject is **discard from the truth path** with an audit record. The
candidate bytes are not admitted at any class. A reject is *not*
silent: the host emits an `AuditRecord` of the rejection and the
matched reject class.

| Class | Trigger |
|---|---|
| R-EXIT | exit `AuditRecord` not durable; G-1 |
| R-DIGEST | host could not compute bytes-returned digest; G-2 |
| R-CAP | capability reconciliation incoherent; G-3 |
| R-SCHEMA | schema nonconformance for a structured artifact; G-4 |
| R-TAINT | undisclosed taint signal in returned bytes; G-5 |
| R-AUDIT-INCOH | host's enter/exit audit pair is incoherent (e.g., conflicting handle catalog) |
| R-SCOPE | bytes contain a non-scope effect signal (e.g., a reference to a path the executor was never granted) |
| R-CHAIN | bytes describe an attempted executor→executor chain |
| R-IMG | bytes were produced under a base-image / engine hash that does not match the host's canonical record |
| R-FORWARD | candidate proposes to forward a capability handle to another session (file `04 F-7`) |

A reject does not consume the producing session's `AuditRecord`; the
session's record remains. The candidate is dropped, and any
downstream lane stage that was waiting on it is notified through the
existing intent / lane state machine (no new contract).

---

## 4. Downgrade rules (D-*)

A downgrade is **admission at a lower replay class**, with a
`DriftEventRecord` (§23.19). The candidate becomes admitted truth at
the lower class only. Per §3.12, downgrade is *never* silent.

| Class | Trigger | Resulting class |
|---|---|---|
| D-TIME | clock dimension short of `exact` (file `06.2`) | one class lower than requested, never above `diagnostic` if no host clock shim used |
| D-RAND | randomness dimension short of `exact` (file `06.3`) | as above |
| D-WORKER | worker determinism dimension short of `exact` (file `06.4`) | typically `semantic`; substrate C defaults to `semantic` |
| D-AUDIT | audit binding dimension complete but partial in detail (e.g., missing handle catalog component) | one class lower; never to `unreplayable` without explicit reject |
| D-RES | resource accounting incomplete (e.g., missing peak RSS) | downgrade to `diagnostic` |
| D-FP | `environment_fingerprint` complete but missing a known-optional field | downgrade only if the missing field is required by the validator's policy |
| D-MULTI | multiple D-* triggers; class is the lowest among all triggered |

A downgrade emits exactly one `DriftEventRecord` per dimension that
fired. Multiple dimensions = multiple `DriftEventRecord`s. The
candidate is admitted at the lowest class consistent with the union
of dimensions (`D-MULTI`).

A downgrade **never** raises a class. A downgrade does **not**
overwrite a reject; if a reject class fires, the candidate is
rejected, period.

---

## 5. Defer rules (DF-*)

A defer is **hold as candidate, no admission, named blocker**. The
bytes remain candidate material; the host may re-attempt ingress
later if the named blocker clears. A defer is audit-emitting; it is
not silent.

| Class | Trigger | Cleared by |
|---|---|---|
| D-COMPOSE | a required input fingerprint is missing for `version_tuple_hash`; G-7 | input fingerprint becomes available |
| D-DOWN-PATH | the downgrade path is wired but a `DriftEventRecord` for this dimension has not been emitted yet (concurrent ingress); G-6 | classifier emits the matching record |
| D-WAL-LAG | exit record is composed but not yet durable (rare; §22.1 transient); G-1 | record reaches durability |
| D-TAINT-PEND | a §22.11 taint propagation walk is in flight that may affect this candidate's taint vector; G-5 | walk completes |
| D-POLICY | the validator's required class is parameterized by a policy version not yet confirmed for this run | policy version confirmed |

A defer that does not clear within the validator's policy deadline
is escalated to a reject (R-DEFER-EXPIRED) with an `AuditRecord`
naming the original defer class and the deadline that was missed.

---

## 6. Ingress invariants

The pipeline obeys the following invariants. Any future implementation
that cannot satisfy them is not admissible.

- **I-1.** A candidate cannot become admitted truth without a host-
  composed `version_tuple_hash` and a host-minted `ReplayAnchor`.
- **I-2.** A candidate's replay class is never raised above the class
  the dimension evidence supports; downgrades are explicit and
  emit `DriftEventRecord`.
- **I-3.** Reject takes precedence over downgrade. Downgrade takes
  precedence over defer. Defer takes precedence over admission.
- **I-4.** A candidate that proposes its own classification is
  treated as if the proposal were absent. Classifier is host-only
  (file `01 §A-8`, `04 §F-12`).
- **I-5.** A candidate that includes any §23.x-shaped object that
  resembles an authority artifact (e.g., a "ReplayAnchor" object) is
  rejected under R-SCHEMA — executors do not produce authority
  artifacts, even bit-identical ones.
- **I-6.** A candidate's bytes-returned digest and the bound digest
  in `AuditRecord(exit)` must agree. Disagreement → R-DIGEST.
- **I-7.** A candidate's `environment_fingerprint` digest (used by
  the host in G-7) is the host's canonical record of the session;
  the executor cannot inject a different value.
- **I-8.** Multiple ingress runs of the same candidate produce the
  same admit / reject / downgrade / defer outcome (deterministic
  ingress, modulo the externally observed conditions in DF-*
  changing). Non-determinism in ingress itself is a defect.
- **I-9.** Ingress must complete in finite time per validator
  policy; an unbounded ingress is itself a reject under R-DEFER-
  EXPIRED.

---

## 7. The candidate-material lifecycle (state diagram, prose form)

```
[exec-exit] ──> CANDIDATE
                 │
                 ├── G-1..G-9 all pass at requested class ──> ADMITTED TRUTH
                 │
                 ├── any G fails with R-* ──────────────────> REJECTED (audit)
                 │
                 ├── G-6 downgrades with D-* ───────────────> ADMITTED TRUTH (lower class) + DriftEventRecord
                 │
                 ├── G-* hits DF-* ────────────────────────> DEFERRED (held as candidate)
                 │                                              │
                 │                                              ├── blocker clears ──> re-enter G-1..G-9
                 │                                              └── deadline missed ─> REJECTED (R-DEFER-EXPIRED)
                 │
                 └── (no fifth path)
```

---

## 8. Net statement

Every byte an external executor returns is candidate material until
the host has *re-derived* its admissibility from host-visible
evidence. Admission is per-byte-set, per-call, audit-bracketed,
class-explicit, and downgrade-honest. Reject, downgrade, and defer
are the only legal failure outcomes; "silently treated as truth" is
a denial under §3.1, §3.2, §3.3, and §3.12, and it does not appear
in any future implementation governed by this package.
