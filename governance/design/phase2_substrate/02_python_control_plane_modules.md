# 02 — Modules That Must Remain Python Control-Plane

Scope: identify modules where Python remains the right language for
Phase 2 even after substrate re-architecture. This is *not* a
commitment to keep them Python forever; it is an honest list of where a
Rust/Wasm rewrite is *not* yet justified by §3.14
replacement-by-evidence.

Selection criteria (all must hold for a module to stay Python):
1. The module is on the **authority** path (issues, validates, or
   adjudicates), so its surface must remain the most reviewable and
   most easily-auditable code in the system (§3.13 minimality at the
   hot path is read here as: clarity > raw throughput).
2. The module is **not** a measured hot path. There is no current
   evidence that Python is the bottleneck for it.
3. The module's correctness is more sensitive to *legibility* under
   audit than to throughput.
4. The module's blast radius on rewrite is large (touches schemas,
   ledgers, drift surfaces). A Rust port would create a multi-week
   re-validation cost that no Phase-1 evidence yet justifies.

## Required-Python modules

| Module (path) | Why it stays Python in Phase 2 |
|---|---|
| `kernel/lifecycle/signable_path_orchestrator.py` | Single most reviewed surface in the system. Stage transitions, fail-closed semantics, audit emission ordering. Legibility dominates. |
| `kernel/lifecycle/stage_types.py` | Pure enum/guard surface. Trivial in Python; no perf benefit from a port. |
| `kernel/lifecycle/signoff_gate.py` | §31 sign-off rule evaluator. Reviewer-facing. Must remain trivially readable and trivially patchable as gates evolve. |
| `kernel/contracts/barrier_rules.py` | C22.3 atomic approval barrier. Authority adjudication. Legibility >> perf. |
| `kernel/contracts/quarantine_rules.py` | C22.4 admissibility checks. Decision logic, not throughput. |
| `kernel/contracts/capability_rules.py` | C22.6 issuance/validation/consume rules. Single most audit-sensitive surface. |
| `kernel/contracts/seal_ordering.py` | C22.1/C22.2 ordering routine. Logic is short; correctness is everything; perf is bounded by SQLite, not by Python. |
| `kernel/services/approval_service.py` | Authority-bearing. Reviewer surface. |
| `kernel/services/review_service.py` | Reviewer-facing artifact assembly. |
| `kernel/services/revision_seal_service.py` | Calls into the storage substrate; perf bounded by SQLite, not by interpreter. |
| `kernel/services/evidence_service.py` + `kernel/evidence/append_only_ledger.py` | Append-only evidence closure. Audit-critical; throughput bounded by storage, not by Python. |
| `kernel/services/budget_governor.py` | Policy adjudication, not arithmetic-bound. |
| `kernel/services/invalidation_service.py` | Drift-reaction logic. Read-time correctness dominates. |
| `kernel/replay/replay_classifier.py` | C22.5 replay class adjudication. Authority surface; legibility dominates over throughput. |
| `kernel/version/version_tuple.py` | Canonical tuple composition. Tiny code, large blast radius. Hash kernel itself can be downshifted later (see `03`); the *composition* logic stays Python. |
| `governance/implementation/*.yaml` consumers (any future loaders) | Governance tooling — Python is the right shape. |

## Why "control plane stays Python" is honest, not ideological

- Python is the substrate the entire reviewer audience already reads
  and patches. Authority code being maximally reviewable is itself a
  §31 sign-off property.
- Moving authority to Rust without measured cause would convert a
  legibility asset into a maintenance liability — exactly the
  "ideological internalization" §27 forbids.
- None of these modules has been demonstrated to be a runtime hot
  spot under Phase-1 tracer-bullet load.

## What this list is **not**

- It is not a permanent ban on Rust in `kernel/`. It is a Phase-2
  posture, replaceable on evidence.
- It does not cover schema validation throughput, hashing, or storage
  internals; those are explicitly considered for downshift in `03`.
- It does not preclude *adding* Rust components alongside; it
  precludes *replacing* the modules above without a triggering
  failure.

## Promotion to "may be ported" requires

Per §3.14:
- a measured, reproducible bottleneck on the module under realistic
  Phase-2 load, *and*
- a written port plan that preserves the module's audit and
  fail-closed semantics, *and*
- a re-validation pack covering every AT/INV the module currently
  satisfies.

Until those exist, these modules stay Python.
