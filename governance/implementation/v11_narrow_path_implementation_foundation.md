# v11 Narrow Path Implementation Foundation

Source-of-truth basis: `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt` (only).

Scope lock: current-stage signable path only:

Context -> Inference -> PatchProposal -> Validation -> Review -> Approval -> Revision Seal -> Evidence

## 1) Implementation Delta Register (v11 -> first buildable baseline)

| Delta ID | Constitutional Anchor | Gap in repository today | Implementation delta (narrow scope) | Proof artifact required |
|---|---|---|---|---|
| D-001 | §24.3, §25.2, §30.2, §31 current-stage signable path | No executable lifecycle scaffolding | Create one linear orchestrator for only the eight-stage signable path; reject any out-of-path operation | Lifecycle trace containing all stage artifacts and stage transition audit records |
| D-002 | §22.7 Context Artifact Completeness | No ContextArtifact schema/validator | Add ContextArtifact schema with completeness checks (provenance/truncation/deferred retrieval mandatory semantics) | Context completeness acceptance tests + invalid artifact rejection evidence |
| D-003 | §23.5 InferenceArtifact | No InferenceArtifact artifactization | Add inference record creation + immutable persisted hash/provenance linkage to ContextArtifact | Inference artifact record + audit append |
| D-004 | §23.6 PatchProposal + §22.13 patch coherence (minimal) | No PatchProposal contract enforcement | Add PatchProposal schema and minimal coherence gate for first slice (single patch class; multi-file forbidden in phase 1) | Proposal admissibility decision record |
| D-005 | §22.4 Validation Quarantine + §23.7/§23.8/§23.9 receipts | No governed validation receipt pipeline | Add one validator lane with quarantine policy object + ValidationReceipt issuance; fail-closed on quarantine violation | Validation receipt + quarantine enter/exit audit records |
| D-006 | §23.10 ReviewArtifact + §22.14 | No governed review artifact | Add review renderer that emits ReviewArtifact with provenance disclosure flag and deterministic diff hash | Review artifact + review provenance query |
| D-007 | §22.3 Atomic Approval Barrier + §23.11 ApprovalArtifact | No approval drift barrier implementation | Add approval barrier checks (root/context/receipt/policy drift) and deterministic fail-closed decisions | Barrier decision audit + drift invalidation record |
| D-008 | §22.1 + §22.2 + §23.1/§23.2/§23.3 | No seal transaction ordering + durable mutation semantics | Implement pending->sealed ordered transaction using SQLite WAL substrate with explicit ordering and durability boundary | Seal-order trace + crash-window classification tests |
| D-009 | §23.14 AuditRecord + Evidence stage obligations | No append-only evidence closure model | Add append-only evidence ledger for every stage transition and decision | Evidence closure report proving full path traceability |
| D-010 | §24.2 invariant binding + §31 sign-off conditions | No mapping from code to invariants | Introduce invariant-binding registry for only first-slice invariants (INV-004/005/006/007/008/015/026/028 as applicable) | Invariant-to-test coverage report |

Implementation narrowing rules for this register:

- No architecture expansion beyond the eight-stage signable path.
- No broadened orchestration shell obligations unless they touch kernel authority.
- Single language, single patch class, single review path, single approval path for tracer-bullet slice.
- **Concrete phase-1 narrowing declaration:** language = Python; patch class = single-file text substitution patch.

## 2) Proposed Repository / Module Layout

```text
governance/
  constitution/
    sovereign_engineering_operating_system_master_plan_v11.txt
  implementation/
    v11_narrow_path_implementation_foundation.md      # this file
    delta_register.yaml                               # machine-readable D-001..D-010
    invariant_bindings.yaml                           # first-slice invariant -> module -> test IDs
    contracts_index.yaml                             # machine-readable C22/C23/C24/C31 extraction index

kernel/
  lifecycle/
    signable_path_orchestrator.py                     # stage machine for 8-step path only
    stage_types.py                                    # Context/Inference/.../Evidence enums + guards
    signoff_gate.py                                   # §31 sign-off condition checker
  version/
    version_tuple.py                                  # canonical ordered version_tuple_hash composer
  replay/
    replay_classifier.py                              # durable replay-classification decision engine
  taint/
    taint_classes.py                                  # canonical C22.11 taint class enum
  contracts/
    contract_ids.py                                   # C22.x IDs and lookup
    barrier_rules.py                                  # Atomic Approval Barrier checks
    seal_ordering.py                                  # ordered seal transaction routine
    quarantine_rules.py                               # validation quarantine admissibility checks
    capability_rules.py                               # capability token issuance/validation/consumption rules
  schemas/
    revision.schema.json
    journal_entry.schema.json
    snapshot_root.schema.json
    context_artifact.schema.json
    inference_artifact.schema.json
    patch_proposal.schema.json
    validation_receipt.schema.json
    review_artifact.schema.json
    approval_artifact.schema.json
    audit_record.schema.json
    drift_event_record.schema.json
    failure_bundle.schema.json
    capability_token.schema.json
    taint_record.schema.json
    budget_record.schema.json
    replay_anchor.schema.json
    intent_anchor_record.schema.json                 # minimal durable causal anchor (execution-layer)
  stores/
    sqlite/
      migrations/
        0001_core_signable_path.sql                   # first narrow schema set
      repositories.py                                 # typed persistence adapters
      wal_recovery.py                                 # WAL continuity + recovery classifiers
  services/
    context_service.py
    inference_service.py
    patch_proposal_service.py
    validation_service.py
    review_service.py
    approval_service.py
    capability_service.py
    revision_seal_service.py
    evidence_service.py
  evidence/
    append_only_ledger.py
    trace_query.py

validation/
  quarantine/
    runner_adapter.py                                 # local runner wrapper with policy checks
  tests/
    acceptance/
      test_at_006_wal_dirty_tail_truncation.py
      test_at_007_wal_midsegment_halt.py
      test_at_008_approval_root_drift.py
      test_at_008_barrier_concurrent_serialization.py
      test_at_009_seal_file_truth_mismatch.py
      test_at_010_quarantine_no_pollution.py
      test_at_011_quarantine_blocks_untrusted_execution.py
      test_at_013_replay_claim_bound.py
      test_at_015_forensic_reconstructability.py
      test_at_016_patch_coherence_minimal.py
      test_at_018_capability_single_use.py
      test_at_018_capability_double_consume_race.py
      test_at_020_review_provenance_governance.py
      test_at_023_worker_lifecycle_transitions.py
      test_at_024_taint_propagation.py
      test_at_028_no_silent_taint_clearing.py
      test_at_033_audit_append_only.py
      test_at_035_drift_consequence_invalidation.py

tests/
  tracer_bullet/
    test_happy_path_context_to_evidence.py
    test_rejection_path_invalid_approval_barrier.py
    test_replay_classification_downgrade.py
    test_signoff_gate_correctness.py
```

Layout intent:

- `kernel/` holds load-bearing authority logic (truth/approval/seal/evidence barriers).
- `governance/implementation` carries machine-readable implementation governance artifacts.
- `validation/` and `tests/` hold acceptance and tracer-bullet proof density.

## 3) Schema Source-of-Truth Plan

1. **Canonical schema set = Section 23 artifact list** for first-slice required objects only.
2. **Schema format**: JSON Schema (draft pinned) under `kernel/schemas/`; each schema includes:
   - `artifact_type`
   - `schema_version`
   - required/optional fields exactly from §23
   - immutability/invalidation metadata
3. **Schema freeze discipline**:
   - initial freeze tag: `v11-slice1`
   - additive-only changes allowed for optional fields in current stage
   - any required-field change demands constitution-aligned migration note in `delta_register.yaml`
4. **Runtime enforcement**:
   - all stage artifacts validated at ingress + pre-persist
   - invalid schema => fail closed + `FailureBundle`
5. **Persistence contract**:
   - SQLite tables generated from frozen schema pack mapping
   - table-level constraints for append-only records (JournalEntry/AuditRecord/FailureBundle)
6. **Traceability**:
   - each persisted artifact stores `version_tuple_hash`
   - evidence queries can reconstruct which schema version admitted each artifact
7. **Authority and taint ledgers (must-fix for coding start)**:
   - SQLite generation must include durable tables for `CapabilityToken` (23.13) and `TaintRecord` (23.17)
   - taint transitions must be append-only and queryable through evidence paths
8. **Hardware-budget traceability (important, later-stage sign-off hardening)**:
   - include `BudgetRecord` (23.16) table in the schema pack now, but allow minimal generation in first tracer bullet
   - context budget decisions (`hard_budget_tokens`, `effective_budget_tokens`) must have explicit budget-record linkage before true slice sign-off
9. **Canonical version tuple composition (must-fix for coding start)**:
   - all artifact-producing services must call one shared `version_tuple.py` module for `version_tuple_hash`
   - **pre-coding constant:** `PHASE1_VERSION_SENTINEL = "phase1-unset-v1"`
   - ordered composition follows §8.2 field order; every non-applicable phase-1 component must use `PHASE1_VERSION_SENTINEL` (never omitted)
   - artifact-producing services must not invent service-local sentinel values
   - drift detection rule: any tuple-field change emits a drift classification input and invalidates cached admissibility where policy requires
10. **Phase-1 temporary budget policy (P1 sign-off readiness item)**:
   - `hard_budget_tokens` and `effective_budget_tokens` in ContextArtifact are populated from a declared static policy maximum (`phase1_budget_policy_v1`)
   - this is an honest temporary rule under §27 and is replaced by full BudgetRecord-linked dynamic budgeting when AT-027 promotion is admitted
11. **Phase-1 memory policy (P1 sign-off readiness item)**:
   - phase 1 admits no memory items; `memory_item_ids = []` is mandatory and schema-valid
   - memory-related provenance refs are empty in phase 1 and this is explicit, not implicit
12. **FilesystemTruthReconciliation (reinforcement-only)**:
   - git remains file-content truth; kernel remains governance truth
   - `SnapshotRoot.root_hash` is grounded in git tree/hash for the admitted repository state
   - out-of-band file edits are treated as drift inputs (never silent truth mutation)
13. **macOS quarantine guarantee classification (phase-1 explicit posture)**:
   - isolation strategy: local macOS runner with policy-governed constraints and explicit taint/receipt downgrade on guarantee shortfall
   - guarantee level: bounded quarantine guarantee (not full container-equivalence claim)
   - receipt posture: quarantine uncertainty or breach suspicion forces taint propagation and receipt trust downgrade
14. **AT-012 anti-swap posture (honest deferral)**:
   - AT-012 is deferred to later hardening and is not a phase-1 coding-start blocker
   - phase-1 coding start remains bounded by current tiny-repo tracer constraints and existing budget/taint safeguards

## 4) Contract-to-Code Extraction Plan (Sections 22 / 23 / 24 / 31)

### 4.1 Extraction mechanics

- Build `contracts_index.yaml` with entries:
  - `contract_id` (e.g., C22.3)
  - `purpose`
  - `required_fields`
  - `required_checks`
  - `legal_rules`
  - `failure_reactions`
  - `acceptance_refs` (AT IDs)
  - `invariant_refs` (INV IDs)
- Generate code stubs per contract entry into `kernel/contracts/*`.
- Bind each contract check to an explicit function-level guard and audit emission point.
- Governance YAML format contract (must-fix):
  - `delta_register.yaml`: `delta_id:str`, `constitution_refs:[str]`, `module_refs:[str]`, `acceptance_refs:[str]`, `status:{planned|in_progress|bound}`
  - `invariant_bindings.yaml`: `invariant_id:str`, `enforcement_module:str`, `enforcement_point:str`, `acceptance_test_ids:[str]`, `failure_reaction:str`
  - `contracts_index.yaml`: `contract_id:str`, `purpose:str`, `required_fields:[str]`, `required_checks:[str]`, `legal_rules:[str]`, `failure_reactions:[str]`, `acceptance_refs:[str]`, `invariant_refs:[str]`

### 4.2 Section 22 extraction focus (current narrow path)

Prioritize contracts directly load-bearing on first signable path:

- C22.1 WAL Durability and Recovery
- C22.2 Seal Transaction Ordering
- C22.3 Atomic Approval Barrier
- C22.4 Validation Quarantine Enforcement
- C22.5 Replay Fidelity Contract (must-fix before coding)
- C22.6 Capability Token Lifecycle (must-fix before coding)
- C22.7 Context Artifact Completeness
- C22.10 Invariant Enforcement Binding
- C22.11 Taint Propagation Graph (taint transitions must be durably recordable)
- C22.13 Multi-File Patch Coherence (phase-1 narrowed behavior)
- C22.14 Review Surface Governance

Authority-boundary concurrency closure (narrow-path substrate-level rule):

- Approval barrier concurrency (C22.3) is serialized via SQLite/WAL transaction serialization plus revision-fence check; concurrent contenders resolve by deterministic one-winner rule and losers fail closed.
- Capability consume concurrency (C22.6) is serialized via atomic token-consumption gate in the same transaction domain; concurrent double-consume resolves deterministically with exactly one winner and explicit rejection evidence for the loser.

ModelIntegrationContract (reinforcement-only, architecture-preserving):

- prompt construction is governed from `ContextArtifact`; no ungoverned prompt surface is admitted
- model responses are parsed through typed response handling before `InferenceArtifact` creation
- timeout/retry/token-budget controls are policy-governed and auditable
- model API failure paths emit `FailureBundle` with causality refs
- model output is never authority; only kernel-governed artifact conversion may advance state

### 4.3 Section 23 extraction focus (artifact schemas)

First slice required schema set:

- ContextArtifact (23.4)
- InferenceArtifact (23.5)
- PatchProposal (23.6)
- ValidationReceipt + BuildReceipt + SemanticReceipt (23.7/23.8/23.9, minimal required subset)
- ReviewArtifact (23.10)
- ApprovalArtifact (23.11)
- CapabilityToken (23.13) **must-fix before coding**
- ReplayAnchor (23.12) **must-fix before coding**
- Revision + JournalEntry + SnapshotRoot (23.1/23.2/23.3)
- AuditRecord + FailureBundle + DriftEventRecord (23.14/23.15/23.19)
- TaintRecord (23.17) **must-fix before coding**
- BudgetRecord (23.16) (important later-stage hardening; included now for schema continuity)
- IntentAnchorRecord (execution-layer minimal causal anchor for §22.1/§22.2 preconditions; intentionally not a broad full-lifecycle artifact)

### 4.4 Section 24 extraction focus (acceptance + invariants)

- Construct `acceptance_registry.yaml` for ATs touched by slice.
- Construct `invariant_bindings.yaml` mapping INV -> module -> enforcement point -> test IDs.
- Block release candidate if any load-bearing slice invariant lacks test binding.

### 4.5 Section 31 extraction focus (sign-off gates)

Implement `signoff_gate.py` that checks, for slice scope:

- core contracts formalized and executable
- frozen schemas present for required slice artifacts
- replay honesty checks active
- capability/approval/side-effect governance active on slice path
- context completeness checks active
- retention/pinning explicitly declared (minimum declaration allowed; full GC pinning can be staged but must be non-silent)
- invariant coverage non-zero and passing for selected slice invariants

## 5) Acceptance Test Plan (first tracer-bullet slice)

### 5.1 Minimum signable slice tests

1. **Happy path lifecycle test**
   - Executes full path: Context -> Inference -> PatchProposal -> Validation -> Review -> Approval -> Revision Seal -> Evidence
   - Asserts every stage emits artifact + audit record, including durable `ReplayAnchor` output at Evidence stage.

2. **Barrier rejection test (root drift)**
   - Approve at root R1, drift to R2 before execute.
   - Approval barrier must fail closed and emit DriftEventRecord.

3. **Validation quarantine enforcement test**
   - Attempt host cache mutation during validation.
   - Must be blocked; receipt invalidated.

4. **Seal durability ordering crash-window tests**
   - Inject crashes around durability boundary checkpoints.
   - Assert no pre-durable sealed visibility; deterministic recovery classification.

5. **Review provenance governance test**
   - Self-summary forbidden policy case must be flagged/rejected.

6. **Evidence append-only test**
   - Attempt mutation of prior AuditRecord.
   - Must fail; append-only invariant preserved.

7. **Replay honesty test (classification bound)**
   - Missing evidence/inference artifact must downgrade or refuse exact replay claim.

8. **Capability token lifecycle test**
   - Consume a single-use token once; second consumption attempt must fail closed.

9. **Taint transition durability test**
   - Trigger taint escalation (e.g., quarantine breach suspect) and assert append-only `TaintRecord` emission + queryability.

10. **Worker lifecycle transition legality test**
   - Reject illegal `created -> completed` direct transition and emit lifecycle audit evidence.

### 5.2 AT/INV mapping for first slice

- AT-008 -> INV-006/INV-007 (approval drift barrier + concurrent serialization one-winner rule)
- AT-010/AT-011 -> INV-008 (quarantine)
- AT-013/AT-032 -> INV-010/INV-011 (replay honesty, durable ReplayAnchor-backed classification)
- AT-016 -> INV-016 (patch coherence)
- AT-020 -> INV-015 (review provenance)
- AT-018 -> INV-012/INV-013 (capability token lifecycle/admissibility + concurrent double-consume deterministic rejection)
- AT-023 -> INV-018 (worker/stage transition legality)
- AT-033 -> INV-026 (audit append-only)
- AT-035 -> INV-028 (drift consequence invalidation)
- AT-024/AT-028 -> INV-019/INV-022 (taint propagation and no silent clearing)
- AT-027 -> INV-021 (budget exhaustion governance; later-stage hardening target)

## 6) Minimal First Build Order

1. **State-machine skeleton + artifact IDs + minimal durable intent causal anchor (P0)**
   - Implement eight-stage orchestrator as explicit state-machine boundaries and artifact identity primitives.
   - Create minimal production causal-anchor record (`intent_id`, `task_id`, `state`, `created_at`) at earliest runnable stage.
   - Fixture-only intent handling is explicitly insufficient for operational sign-off.
2. **Frozen schemas + persistence migration (SQLite WAL)**
   - Add first-slice schema files and DB migration with append-only constraints, including `CapabilityToken`, `TaintRecord`, and `ReplayAnchor`.
   - Include `BudgetRecord` table as forward-compatible hardening surface (non-blocking for day-1 tiny-repo tracer bullet).
3. **Version tuple + replay classifier foundation (P0)**
   - Implement canonical `version_tuple_hash` composition module and shared import path for all artifact-producing services.
   - Implement replay classifier that emits durable replay-classification artifacts (`ReplayAnchor`) for AT-013/AT-032 evidence closure.
4. **Capability gate bootstrap + context wiring (P0)**
   - Implement capability issuance/validation/consume checks and bind C22.6 to orchestrator stage gates.
   - Wire repository-read/snapshot-read capability verification into context admission from the start (not as later integration).
5. **Context/Inference/PatchProposal services**
   - Artifactize upstream proposal path before authority-bearing gates.
6. **Validation service + quarantine enforcement + taint emission**
   - Introduce governed receipt issuance, contamination protections, and append-only taint transition emission.
7. **Review + Approval barrier**
   - Add review provenance checks, then atomic approval barrier.
8. **Seal ordering + recovery classifier + crash-window tests (P0)**
   - Implement legal pending->sealed ordering and concrete crash-window classification backed by AT-006/AT-007/AT-009 tests.
9. **Evidence ledger + audit queries**
   - Ensure every stage decision is reconstructable, including capability, replay, and taint lifecycle queries.
10. **Tracer-bullet tests + signoff gate proof**
   - Execute minimum acceptance matrix slice and signoff-gate correctness tests before declaring coding-start readiness for signable-path execution.

Definition of done for this first implementation foundation:

- narrow signable path implemented end-to-end (single lane, single class)
- rejection path implemented and evidenced
- replay classification bound by evidence
- append-only audit evidence queryable
- sign-off gate reports pass/fail against slice obligations only

## 7) Audit Mapping: Delta Items -> Exact v11 Section References

| Delta ID | Exact v11 references | Why this delta is required for signable path |
|---|---|---|
| D-001 | §24.3, §25.2, §26, §30.2, §31 | These sections explicitly define the current-stage signable path and tracer-bullet narrowness; lifecycle scaffolding is required to prove governed closure. |
| D-002 | §22.7, §23.4, §31 | Context completeness and frozen ContextArtifact semantics are mandatory for admissible review/approval/replay use. |
| D-003 | §23.5, §24.3, §26 | Inference must be artifactized (not trusted raw) in the signable sequence. |
| D-004 | §23.6, §22.13, §26 | PatchProposal must be governed; coherence obligations exist even when phase-1 narrows to one patch class. |
| D-005 | §22.4, §23.7, §23.8, §23.9, §24.2 (INV-008), §31 | Validation must be real and quarantine-governed; receipts become approval-relevant authority inputs. |
| D-006 | §22.14, §23.10, §24.2 (INV-015), §26 | Review requires admissible artifact and provenance disclosure before approval conversion. |
| D-007 | §22.3, §23.11, §24.2 (INV-006, INV-007), §31 | Approval must fail closed across drift/races and cannot time-travel into execution authority. |
| D-008 | §22.1, §22.2, §23.1, §23.2, §23.3, §24.2 (INV-004, INV-005), §27 | Sealing must obey WAL durability/order and deterministic crash semantics. |
| D-009 | §15, §23.14, §24.2 (INV-026), §31 | Evidence closure and append-only auditability are sign-off requirements. |
| D-010 | §22.10, §24.1, §24.2, §31 | Load-bearing invariants must bind to enforcement points and acceptance coverage. |

## 8) Audit Mapping: Proposed Modules -> Contract / Schema / Acceptance Obligations

| Module | Contract obligations (Section 22) | Schema obligations (Section 23) | Acceptance / Invariant obligations (Section 24) | Scope marker |
|---|---|---|---|---|
| `kernel/lifecycle/signable_path_orchestrator.py` | C22.5 replay admission boundary, C22.6 capability-gated stage admission, C22.9 interface boundaries, C22.10 invariant bindings | Emits/links 23.4/23.5/23.6/23.7/23.10/23.11/23.1/23.12/23.14 | AT-008/010/013/016/018/020/023/032/033/035; INV-006/008/010/011/012/015/016/018/026/028 | Narrow-path load-bearing (P0) |
| `kernel/lifecycle/stage_types.py` | C22.10 binding for legal transition surfaces | Stage enum/transition guards over 23.x artifact boundaries | AT-023; INV-018 | Narrow-path load-bearing (P0 FSM binding) |
| `kernel/contracts/barrier_rules.py` | C22.3 | Consumes 23.11 + 23.4 + 23.7/23.8/23.9 + 23.19 | AT-008, AT-035; INV-006, INV-007, INV-028 | Narrow-path load-bearing |
| `kernel/contracts/seal_ordering.py` | C22.1, C22.2 | Produces 23.1/23.2/23.3 + 23.14/23.15 on failure | AT-006/007/009 (+ slice crash tests); INV-004, INV-005 | Narrow-path load-bearing |
| `kernel/contracts/quarantine_rules.py` | C22.4 | Governs trust on 23.7/23.8/23.9 + taint/failure records | AT-010, AT-011; INV-008 | Narrow-path load-bearing |
| `kernel/contracts/capability_rules.py` | C22.6 | Governs 23.13 token issuance/validation/consumption/admissibility | AT-018; INV-012/INV-013 | Narrow-path load-bearing (must-fix) |
| `kernel/schemas/*.schema.json` | C22.10 (binding), C22.7 (context completeness) | Direct freeze of selected §23 artifacts, including 23.13/23.17/23.16/23.12 | AT coverage gated via schema-validation assertions in slice tests | Narrow-path load-bearing |
| `kernel/version/version_tuple.py` | C22.10 binding support + §8 tuple discipline | Computes canonical `version_tuple_hash` for all 23.x artifacts that require it | AT-version-tuple-consistency (defined in signoff-gate proof bundle) | Narrow-path load-bearing (P0) |
| `kernel/replay/replay_classifier.py` | C22.5 replay fidelity contract | Produces 23.12 ReplayAnchor | AT-013/AT-032; INV-010/INV-011 | Narrow-path load-bearing (P0) |
| `kernel/taint/taint_classes.py` | C22.11 taint class canonicalization | Constrains 23.17 taint_class vocabulary | AT-024/AT-028; INV-019/INV-022 | Narrow-path load-bearing (P0) |
| `kernel/stores/sqlite/wal_recovery.py` | C22.1, C22.2 | Reads/writes 23.2 + 23.1 recovery state | AT-006, AT-007, AT-009; INV-004, INV-005 | Narrow-path load-bearing |
| `kernel/stores/sqlite/repositories.py` | FilesystemTruthReconciliation (git file-content truth; kernel governance truth) + C22.1 durability boundary support | Grounds SnapshotRoot/root-hash linkage (23.3) to git tree/hash + emits drift input refs (23.19) on out-of-band edits | Supports AT-009 truth-mismatch abort path + AT-035 drift consequence visibility | Narrow-path load-bearing (traceability hygiene) |
| `kernel/services/context_service.py` | C22.7 | 23.4 | Supports AT-013 preconditions via provenance completeness | Narrow-path load-bearing |
| `kernel/services/inference_service.py` | C22.9 crossing discipline + ModelIntegrationContract (governed prompt from ContextArtifact, typed parse before InferenceArtifact, timeout/retry/token-budget governance, API-failure->FailureBundle, no-model-output-authority) | 23.5 + FailureBundle linkage (23.15) on API failure | Supports replay honesty checks AT-013/AT-032; model integration governance evidence | Narrow-path load-bearing |
| `kernel/services/patch_proposal_service.py` | C22.13 (narrowed) | 23.6 | AT-016; INV-016 | Narrow-path load-bearing |
| `kernel/services/validation_service.py` | C22.4, C22.12 (narrow reuse posture) | 23.7/23.8/23.9 | AT-010/011/017; INV-008/INV-017 | Narrow-path load-bearing (INV-017 as adjacent hardening) |
| `kernel/services/review_service.py` | C22.14 | 23.10 | AT-020; INV-015 | Narrow-path load-bearing |
| `kernel/services/approval_service.py` | C22.3 | 23.11, 23.19 | AT-008/AT-035; INV-006/007/028 | Narrow-path load-bearing |
| `kernel/services/capability_service.py` | C22.6 | 23.13 | AT-018; INV-012/INV-013 | Narrow-path load-bearing (must-fix) |
| `kernel/services/revision_seal_service.py` | C22.1, C22.2 | 23.1/23.2/23.3 | AT-006/007/009; INV-004/005 | Narrow-path load-bearing |
| `kernel/services/evidence_service.py` + `kernel/evidence/append_only_ledger.py` | C22.5 replay evidence closure, C22.10 (binding), C22.11 taint visibility | 23.12/23.14/23.15/23.17 | AT-013/AT-032/AT-033/AT-035/AT-024/AT-028; INV-010/011/026/028/019/022 | Narrow-path load-bearing |
| `validation/quarantine/runner_adapter.py` | C22.4 + macOS phase-1 quarantine guarantee classification (isolation posture + guarantee-level classification + shortfall downgrade) | receipt taint semantics 23.7/23.8/23.9 + taint downgrade linkage (23.17) | AT-010/011 + quarantine guarantee shortfall downgrade assertions | Narrow-path load-bearing |
| `validation/tests/acceptance/*` + `tests/tracer_bullet/*` | C22.10 (proof binding) | N/A (exercise all selected schemas) | Explicit AT/INV proof closure | Narrow-path load-bearing |
| `governance/implementation/delta_register.yaml` | C22.10 | maps to all selected §23 artifacts | traceability for AT/INV binding completeness | Narrow-path governance support |
| `governance/implementation/invariant_bindings.yaml` | C22.10 | N/A | direct INV -> enforcement/test mapping | Narrow-path governance support |
| `kernel/lifecycle/signoff_gate.py` | §31 sign-off rule + C22.10 binding checks | Reads schema/version obligations across selected 23.x artifacts | test_signoff_gate_correctness + proof that gate rejects unmet §31 conditions | P1 required before sign-off |

## 9) Audit Mapping: Acceptance Items -> Explicit AT / INV Coverage

| Acceptance item in this foundation | Explicit AT coverage | Explicit INV coverage | Coverage status |
|---|---|---|---|
| Happy path lifecycle through 8 stages with evidence closure | AT-022 (approval gating relevance), AT-033 (audit append-only) | INV-009 (raw side effects forbidden), INV-026 | Partial in first slice; full side-effect coverage deferred |
| Barrier rejection on root drift | AT-008, AT-035 | INV-006, INV-007, INV-028 | Required in first slice |
| Validation quarantine host-pollution rejection | AT-010, AT-011 | INV-008 | Required in first slice |
| Seal durability ordering crash-window behavior | AT-006, AT-007, AT-009 | INV-004, INV-005 | Required in first slice |
| Review provenance governance | AT-020 | INV-015 | Required in first slice |
| Evidence append-only integrity | AT-033 | INV-026 | Required in first slice |
| Replay honesty downgrade/refusal | AT-013, AT-032 | INV-010, INV-011 | Required in first slice |
| Patch coherence (narrowed first slice) | AT-016 | INV-016 | Required in first slice |
| Capability token lifecycle and admissibility | AT-018 | INV-012, INV-013 | Required in first slice (must-fix) |
| Taint transition durability and no silent clearing | AT-024, AT-028 | INV-019, INV-022 | Required in first slice (must-fix for taint-governed evidence) |
| Incremental invalidation behavior (optional in first tracer bullet, hardening-adjacent) | AT-017 | INV-017 | Marked adjacent hardening / not day-1 blocker |
| Budget exhaustion governance behavior | AT-027 | INV-021 | Later-stage hardening target; schema included now |
| Forensic reconstructability (scope-limited phase-1 interpretation) | AT-015 | INV-027 (indirect via failure evidence retention path) | P2 cleanup: phase-1 limits to FailureBundle/retention evidence, not full encrypted vault |

## 10) Scope Audit Flags (Anything exceeding narrow current-stage signable path)

The following previously proposed items exceed strict first-slice implementation closure and are therefore flagged as **not required to sign the first narrow path**:

- Broad module surfaces that imply multi-lane orchestration beyond one linear signable lifecycle.
- Full generalized route policy engine behavior (multi-vendor route optimization) beyond single worker profile tracer bullet.
- Full GC pinning implementation machinery (allowed as declared policy surface; deep implementation belongs to later hardening stages).
- Broad incremental validation optimization engine (full dependency graph sophistication) beyond minimal correctness checks needed for first slice.
- Any broader Project OS shell ergonomics, dashboards, backlog orchestration, or multi-lane runtime UX.

Disposition rule:

- Keep as explicitly marked future hooks only.
- Do not treat as current-stage sign-off blockers unless they directly weaken kernel authority surfaces on the narrow path.

## 11) Scope Classification: Outer Orchestration / Later Stage / Non-Blocking Future Scope

| Item | Classification | Constitutional basis | Current-stage blocker? |
|---|---|---|---|
| Rich lane orchestration / async backlog shell | Outer orchestration shell | §25.1, §30.5 | No (unless touching kernel authority) |
| Multi-vendor routing sophistication/benchmark breadth | Later-stage hardening/expansion | §28 (order), §30.6 | No for first slice |
| Full GC pinning and retention traversal depth | Hardening-stage kernel strengthening | §28 order includes GC pinning | Not day-1 blocker if minimum explicit retention declarations exist |
| Broad project OS command-center behavior | Outer shell future scope | §25.1, §30.5 | No |
| Domain adapter surfaces / non-text domains | Out of current first-class scope | §2.3, §2.5 | No (and excluded) |
| AT-012 anti-swap watermark enforcement | Later hardening (hardware-pressure governance) | §5.2/§5.3, §28 hardening order | No for phase-1 coding start (explicitly deferred) |

## 12) Constitutional File Modification Confirmation

Explicit confirmation:

- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt` was **not modified** in this review-preparation step.
- This step only refines the extraction artifact for audit-readiness and mapping clarity.

## 13) Review-Preparation Compliance Matrix (explicit closure of requested audit additions)

This section is added to make audit readiness mechanically obvious for reviewers.

| Requested addition | Where satisfied in this artifact | Explicit status |
|---|---|---|
| 1) Map every delta item to exact v11 section references | Section 7 (`D-001`..`D-010` each mapped to exact § references) | Complete |
| 2) Map every proposed module to exact contract/schema/acceptance obligations | Section 8 module mapping table | Complete |
| 3) Map every proposed acceptance item to explicit AT/INV coverage | Section 9 acceptance mapping table | Complete |
| 4) Mark anything that exceeds narrow current-stage signable path | Section 10 scope-audit flags | Complete |
| 5) Mark anything belonging to outer orchestration shell / later-stage / non-blocking future scope | Section 11 scope classification table | Complete |
| 6) Explicitly confirm whether constitutional file was modified | Section 12 explicit confirmation statement | Complete |

### 13.1 No-broadening confirmation (review-preparation guardrail)

- This document remains a review artifact only.
- No production code was introduced in this step.
- No new architecture was proposed in this step.
- No scope expansion beyond the current-stage signable path is authorized by this artifact.


## 14) Formal Response to Audit Findings (Gemini input)

This section records disposition decisions and exact obligation mappings while preserving narrow-path scope.

### AUDIT-001 — CapabilityToken / C22.6 / 23.13

- **Disposition:** Accept.
- **Rationale:** This is a constitutional must-fix because default-deny and capability-gated execution are load-bearing for validation/quarantine and side-effect authority.
- **v11 obligation mapping:** §3.2 (default deny), §22.6 (Capability Token Lifecycle Contract), §23.6 (`capability_requirements` in PatchProposal), §23.13 (CapabilityToken), §24.1 AT-018, §24.2 INV-012/INV-013, §31 sign-off authority controls.
- **Artifact updates in this document:**
  - Added `kernel/contracts/capability_rules.py` in Section 2 layout.
  - Added `CapabilityToken` to Section 4.3 required schema set.
  - Added capability ledger requirement to Section 3 persistence plan.
  - Added capability bootstrap and AT-018 coverage in Sections 5 and 6.

### AUDIT-002 — TaintRecord / 23.17 / taint ledger

- **Disposition:** Accept.
- **Rationale:** Taint-bearing artifacts already require `taint_set`; without durable taint transition records, taint governance and replay/audit downgrade reasoning are not provable.
- **v11 obligation mapping:** §22.11 (Taint Propagation Graph Contract), §23.17 (TaintRecord), §23.4/23.6/23.7/23.10 (`taint_set` fields), §24.1 AT-024/AT-028, §24.2 INV-019/INV-022, §31 audit/replay integrity requirements.
- **Artifact updates in this document:**
  - Added `taint_record.schema.json` to Section 2 layout and Section 4.3 schema list.
  - Added taint ledger requirement in Section 3 persistence plan.
  - Bound evidence service responsibilities to taint transition emission in Section 6 and mapping tables.

### AUDIT-003 — IntentArtifact / causal anchor

- **Disposition:** Partially accept (current-stage constrained).
- **Rationale:** Causal anchoring is valid and important; however, introducing a new formal top-level artifact type beyond the frozen §23 pack would broaden scope at this stage. For narrow-slice legality, the artifact now requires a minimal **durable production** intent causal anchor (`intent_id`, `task_id`, `state`, `created_at`) created at the earliest runnable stage and bound to `Revision.intent_id`/WAL preconditions.
- **v11 obligation mapping:** §22.1 precondition (`valid originating intent exists`), §23.1 (`intent_id` required in Revision), §31 sign-off honesty rule (no overclaiming unimplemented surfaces).
- **Artifact updates in this document:**
  - Replaced fixture-only intent handling with an early minimal durable causal-anchor requirement in Section 6 (no broad full-lifecycle intent architecture introduced).

### AUDIT-004 — BudgetRecord / hardware-aware budget closure

- **Disposition:** Partially accept (important later-stage, included as forward-compatible extraction).
- **Rationale:** Hardware/budget governance is real, but day-1 tracer bullet can remain tiny-repo constrained. To prevent future schema debt, include `BudgetRecord` in extraction now and bind AT-027 as hardening target.
- **v11 obligation mapping:** §5.2/§5.3 hardware and anti-swap posture, §23.16 BudgetRecord, §24.1 AT-027, §24.2 INV-021, §28 hardening order and proof density.
- **Artifact updates in this document:**
  - Added `budget_record.schema.json` and schema/persistence mention.
  - Added AT-027 / INV-021 mapping as later-stage hardening target.

### AUDIT-005 — FSM orchestrator strength improvement

- **Disposition:** Accept as strong improvement, adopted early without widening scope.
- **Rationale:** Explicit state transitions improve auditability and aligns with worker lifecycle invariants while remaining inside the same eight-stage path.
- **v11 obligation mapping:** §9 state model intent, §24.2 INV-018 (legal lifecycle transitions), §31 sign-off evidence clarity.
- **Artifact updates in this document:**
  - Section 6 now specifies state-machine boundaries for the orchestrator (still narrow path, no surface expansion).

Scope protection note:

- These responses do **not** authorize broader production coding.
- The constitutional file remains unchanged; updates are extraction-artifact only.


## 15) Change Summary

### Updated in this revision

- Closed P0 extraction gaps for replay closure, version tuple closure, capability enforcement integration, taint closure, minimal durable intent causal anchor, seal-proof test-file concreteness, and FSM binding to AT-023/INV-018.
- Added P1 clarifications for temporary budget policy, empty-array memory policy, signoff-gate proof binding, and concrete phase-1 narrowing declaration (Python + single-file text substitution patch).
- Preserved narrow eight-stage signable path and constitutional backbone while avoiding production-code implementation in this step.

### Intentionally deferred

- P2 items remain deferred as documented: deeper contracts-index formalization hardening, AT-015 broader vault semantics, and explicit inter-plane crossing appendix (optional/later-stage detail refinement).

## 16) Coding Start Readiness

- **Coding-start posture:** clean coding-start ready for tightly controlled first-slice foundation work.
- **Execution permission wording:** coding may begin for tightly controlled first-slice foundation work with the explicit carrier mappings in Section 18 treated as mandatory acceptance gates.


## 17) Final Capability-Security Invariant Closure (minimum first-slice subset)

This section closes only the minimum §19.1 capability-security subset needed for first-slice authority closure.

| invariant_id | enforcement_module | enforcement_point | proof / acceptance intent | first-slice status |
|---|---|---|---|---|
| INV-CAP-ONLY-KERNEL-ISSUED | `kernel/contracts/capability_rules.py` + `kernel/lifecycle/signable_path_orchestrator.py` | capability issuance boundary + stage-admission authority check | prove only kernel-issued capabilities are admissible as live authority | Required |
| INV-CAP-VERIFY-BEFORE-EFFECT | `kernel/contracts/capability_rules.py` + `kernel/lifecycle/signable_path_orchestrator.py` | pre-effect stage gate (context read admission, validation entry, seal/evidence effect boundary) | prove verification is executed before any effect-bearing action | Required |
| INV-CAP-SINGLE-USE-MEANS-SINGLE-USE | `kernel/contracts/capability_rules.py` | token consumption gate | prove single-use token cannot be consumed twice | Required (AT-018) |
| INV-CAP-NO-DRIFT-CARRYOVER | `kernel/services/approval_service.py` + `kernel/contracts/capability_rules.py` | root/task drift check on bound token | prove drift invalidates token admissibility | Required (AT-008 + AT-035 linkage) |
| INV-CAP-REVOCATION-WINS | `kernel/contracts/capability_rules.py` | revocation check before consumption/admission | prove revoked tokens are always rejected over stale local/UI state | Required (AT-018 revocation branch) |
| INV-CAP-NO-CROSS-CLASS-ESCALATION | `kernel/contracts/capability_rules.py` | capability class vs requested action-class admissibility check | prove lower class cannot escalate to higher effect class | Required (AT-018 + approval-path rejection assertions) |
| INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED | `kernel/contracts/capability_rules.py` + `kernel/stores/sqlite/wal_recovery.py` | ambiguous consume/recover window classifier | prove ambiguous post-crash consumption resolves fail-closed | Required (paired with AT-006/AT-007 crash-window harness) |
| INV-CAP-UI-STATE-IS-NOT-AUTHORITY | `kernel/lifecycle/signable_path_orchestrator.py` + `kernel/lifecycle/signoff_gate.py` | authority source check at stage admission and signoff evaluation | prove UI/presentation state cannot authorize execution without valid capability evidence | Required (signoff gate proof + tracer rejection path) |

Deferral statement:

- No deferral among the required constitutional subset listed above; each is first-slice required and explicitly bound.
- Broader capability-security invariants outside this constitutional minimum subset are deferred to later hardening without weakening first-slice authority closure.

## 18) Final Mechanical AT-to-Test Carrier Matrix (required first-slice AT set)

Every AT listed below is first-slice required and has an explicit carrier.

| AT ID | Required in first slice? | Exact carrier |
|---|---|---|
| AT-006 | Yes | `validation/tests/acceptance/test_at_006_wal_dirty_tail_truncation.py` |
| AT-007 | Yes | `validation/tests/acceptance/test_at_007_wal_midsegment_halt.py` |
| AT-008 | Yes | `validation/tests/acceptance/test_at_008_approval_root_drift.py` + `validation/tests/acceptance/test_at_008_barrier_concurrent_serialization.py` |
| AT-009 | Yes | `validation/tests/acceptance/test_at_009_seal_file_truth_mismatch.py` |
| AT-010 | Yes | `validation/tests/acceptance/test_at_010_quarantine_no_pollution.py` |
| AT-011 | Yes | `validation/tests/acceptance/test_at_011_quarantine_blocks_untrusted_execution.py` |
| AT-013 | Yes | `validation/tests/acceptance/test_at_013_replay_claim_bound.py` + `tests/tracer_bullet/test_replay_classification_downgrade.py` |
| AT-016 | Yes | `validation/tests/acceptance/test_at_016_patch_coherence_minimal.py` |
| AT-018 | Yes | `validation/tests/acceptance/test_at_018_capability_single_use.py` + `validation/tests/acceptance/test_at_018_capability_double_consume_race.py` |
| AT-020 | Yes | `validation/tests/acceptance/test_at_020_review_provenance_governance.py` |
| AT-023 | Yes | `validation/tests/acceptance/test_at_023_worker_lifecycle_transitions.py` |
| AT-024 | Yes | `validation/tests/acceptance/test_at_024_taint_propagation.py` |
| AT-028 | Yes | `validation/tests/acceptance/test_at_028_no_silent_taint_clearing.py` |
| AT-032 | Yes | `tests/tracer_bullet/test_replay_classification_downgrade.py` |
| AT-033 | Yes | `validation/tests/acceptance/test_at_033_audit_append_only.py` |
| AT-035 | Yes | `validation/tests/acceptance/test_at_035_drift_consequence_invalidation.py` |

## 19) Final Residual + Coding-Start Status

- **Remaining explicit residuals:** none for the required final-closure items in this pass.
- **Coding-start status:** clean coding-start ready for tightly controlled first-slice foundation work, with Section 18 carriers treated as mandatory gates.


## 20) Reinforcement Patch Completion

- Reinforcement patch complete.
- The baseline architecture, narrow signable path, and constitutional backbone were preserved.
- The proposed 3-field active version tuple replacement was not adopted; canonical version-tuple posture remains unchanged.
