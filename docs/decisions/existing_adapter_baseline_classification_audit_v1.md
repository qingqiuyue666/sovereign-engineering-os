# Existing Adapter Baseline Classification Audit V1

## Scope

This is a narrow docs-only decision audit that classifies the existing adapter
baseline already present in authoritative `origin/main` before retrying any
non-runtime adapter skeleton marker package.

This is a decision audit only.

This is not adapter implementation.
This is not runtime adapter implementation.
This is not adapter code.
This is not adapter interface code.
This is not adapter skeleton code.
This is not Python files.
This is not `__init__.py`.
This is not Python modules.
This is not Python packages.
This is not Python classes.
This is not dataclasses.
This is not protocols.
This is not schemas.
This is not validators.
This is not tests.
This is not runtime functions.
This is not CLI commands.
This is not repository calls.
This is not service calls.
This is not executor hooks.
This is not runtime authority.
This is not execution capability.
This is not service integration.
This is not DB/UoW integration.
This is not evidence/audit append integration.
This is not executor integration.
This is not restore integration.
This is not subprocess/tool execution.
This is not network integration.
This is not external tool control.
This is not broad physical I/O.
This is not durable writes.
This is not irreversible actions.
This is not a new governance boundary family.
This is not Personal AI Execution OS.
This is not Business Delivery OS.
This is not Creative Production OS.
This is not Research Decision OS.

This audit does not delete files. This audit does not move files. This audit
does not modify production code. This audit does not modify tests. This audit
does not modify acceptance tests. This audit does not modify examples. This
audit does not modify examples code. This audit does not modify README.md. This
audit does not modify docs/current_phase.md. This audit does not modify the
public overview document. This audit does not modify the dry-run manifest
fixture. This audit does not modify the dry-run manifest fixture usage doc. This
audit does not modify the lifecycle implementation. This audit does not modify
the replay verifier. This audit does not modify the controlled demo. This audit
does not modify the narrow adapter contract document. This audit does not
modify the narrow adapter skeleton design document.

This audit does not create adapter skeleton marker files. This audit does not
create `kernel/adapters/README.md`. This audit does not create
`kernel/adapters/narrow/README.md`. This audit does not create
`kernel/adapters/narrow/contract_notes.md`. This audit does not create
`kernel/adapters/narrow/non_authority.md`. This audit does not create
`kernel/adapters/narrow/forbidden_operations.md`. This audit does not create
`kernel/adapters/narrow/future_gate.md`.

This audit does not implement adapter. This audit does not add runtime adapter
implementation. This audit does not add adapter code. This audit does not add
adapter interface code. This audit does not add adapter skeleton code. This
audit does not add Python files. This audit does not add `__init__.py`. This
audit does not add Python modules. This audit does not add Python packages. This
audit does not add Python classes, dataclasses, protocols, schemas, validators,
tests, runtime functions, CLI commands, repository calls, service calls, or
executor hooks. This audit does not add runtime. This audit does not add runtime
authority. This audit does not add execution capability. This audit does not
add executor. This audit does not add DB/repository/UoW. This audit does not
add evidence/audit append. This audit does not add restore service. This audit
does not add subprocess. This audit does not add network. This audit does not
add tool execution. This audit does not add external tool control. This audit
does not add multi-file lifecycle. This audit does not add broad physical I/O.
This audit does not add durable writes. This audit does not add irreversible
actions.

This audit does not start Business Delivery OS, Personal AI Execution OS,
Creative Production OS, or Research Decision OS.

## Checkpoint Basis

Current required checkpoint:

- `adapter-baseline-reconciliation-decision-audit-v1`

Authoritative `origin/main` HEAD verified before this branch:

- `662d28959f84a08067dcdcfa7351f626567d2c40`

Required prior reconciliation verdict:

- `BLOCK_MARKERS_PENDING_ADAPTER_BASELINE_RECONCILIATION`

Required next package from prior reconciliation audit:

- `existing-adapter-baseline-classification-audit-v1`

Existing checkpoint tag:

- `seos-narrow-kernel-checkpoint-v1`

Tagged commit:

- `bb9e6f6bfe79d1d5a6aa14810b3a517fb6af6e58`

Existing GitHub Release:

- id: `320261350`
- title: `SEOS narrow kernel checkpoint v1`
- target tag: `seos-narrow-kernel-checkpoint-v1`
- state: draft
- assets: none

## Preserved Stop Rules

This audit explicitly preserves:

- `STOP_BEFORE_ADAPTER_IMPLEMENTATION`
- adapter implementation remains not authorized by default
- direct adapter implementation remains rejected unless a later explicit audit
  proves concrete hard blockers and authorizes a narrow implementation
- existing adapter baseline classification does not authorize new adapter
  implementation
- existing adapter baseline classification does not authorize runtime authority
- existing adapter baseline classification does not authorize execution
  capability
- existing adapter baseline classification does not authorize external tool
  control
- existing adapter baseline classification does not authorize Business /
  Personal / Creative / Research OS
- existing adapter files may not be deleted by this audit
- existing adapter files may not be moved by this audit
- existing adapter files may not be modified by this audit
- no adapter code may be added by this audit
- no adapter marker files may be added by this audit
- no runtime may be authorized by this audit
- no execution capability may be created by this audit
- no service call may be introduced by this audit
- no DB/UoW may be introduced by this audit
- no executor may be introduced by this audit
- no subprocess/network/tool execution may be introduced by this audit
- no external tool control may be introduced by this audit

Adapter implementation remains not authorized by default.
Direct adapter implementation remains rejected unless a later explicit audit
proves concrete hard blockers and authorizes a narrow implementation.
Existing adapter baseline classification does not authorize new adapter
implementation.
Existing adapter baseline classification does not authorize runtime authority.
Existing adapter baseline classification does not authorize execution
capability.
Existing adapter baseline classification does not authorize external tool
control.
Existing adapter baseline classification does not authorize Business /
Personal / Creative / Research OS.
Existing adapter files may not be deleted by this audit.
Existing adapter files may not be moved by this audit.
Existing adapter files may not be modified by this audit.
No adapter code may be added by this audit.
No adapter marker files may be added by this audit.
No runtime may be authorized by this audit.
No execution capability may be created by this audit.
No service call may be introduced by this audit.
No DB/UoW may be introduced by this audit.
No executor may be introduced by this audit.
No subprocess/network/tool execution may be introduced by this audit.
No external tool control may be introduced by this audit.

## Existing Adapter Baseline Classification

Classification:
PRE_EXISTING_PHASE1_REAL_MODEL_IGNITION_ADAPTER_LANE

Classified files:

- `kernel/adapters/__init__.py`
- `kernel/adapters/anthropic_adapter.py`

Related opt-in live test surfaces, if detected:

- `tests/tracer_bullet/test_real_adapter_live_ignition.py`
- `tests/tracer_bullet/test_real_fix_tracer_live.py`
- `tests/tracer_bullet/test_real_adapter_live_failure_ignition.py`

Classification details:

- location: `kernel/adapters/`
- package file: `kernel/adapters/__init__.py`
- adapter file: `kernel/adapters/anthropic_adapter.py`
- provider: Anthropic Messages API
- default replay ceiling: semantic
- default CI posture: no live network execution unless opt-in tests are
  explicitly enabled
- authority posture: not general runtime authority
- execution posture: not general execution capability
- expansion posture: does not authorize new adapter implementation
- marker implication: future non-runtime marker files should not assume
  `kernel/adapters/` is empty or marker-only

This classification preserves the existing adapter lane as a pre-existing
phase-1 real-model ignition lane. It does not convert that lane into general
runtime authority, general execution capability, general adapter authorization,
external tool control, or OS-level automation authorization.

## Evidence Summary

The authoritative baseline contains `kernel/adapters/__init__.py` before any
marker package. The package file describes real-model adapters and identifies
`anthropic_adapter.AnthropicMessagesAdapter` as the Anthropic Messages API
adapter.

The authoritative baseline contains `kernel/adapters/anthropic_adapter.py`
before any marker package. The adapter file defines
`AnthropicMessagesAdapter`, names `https://api.anthropic.com/v1/messages`,
imports `InferenceFailure` and `InferencePolicy` from the inference service
boundary, uses stdlib `urllib.request`, and declares
`REPLAY_CEILING = "semantic"`.

Tests refer to `AnthropicMessagesAdapter`. Live-provider surfaces are gated by
opt-in environment variables including `SOS_RUN_LIVE_ANTHROPIC` and
`ANTHROPIC_API_KEY`.

The repository also contains:

- `docs/contracts/narrow_adapter_contract_v1.md`
- `docs/design/narrow_adapter_skeleton_design_v1.md`

The current phase still states:

- adapter implementation: not eligible by default

## Decision Questions

1. Whether `kernel/adapters/__init__.py` exists before any marker package.

Answer: Yes.

2. Whether `kernel/adapters/anthropic_adapter.py` exists before any marker
   package.

Answer: Yes.

3. Whether those files are newly introduced by this audit.

Answer: No.

4. Whether those files are deleted, moved, or modified by this audit.

Answer: No.

5. Whether the existing adapter baseline should be classified before retrying
   marker files.

Answer: Yes.

6. Whether `kernel/adapters/__init__.py` describes an existing real-model
   adapter package.

Answer: Yes.

7. Whether `kernel/adapters/anthropic_adapter.py` is a real-model Anthropic
   Messages API adapter.

Answer: Yes.

8. Whether `kernel/adapters/anthropic_adapter.py` is documentation-only.

Answer: No.

9. Whether `kernel/adapters/anthropic_adapter.py` is non-runtime marker content.

Answer: No.

10. Whether `kernel/adapters/anthropic_adapter.py` is actual Python adapter
    code.

Answer: Yes.

11. Whether the existing Anthropic adapter should be classified as a
    pre-existing phase-1 real-model ignition adapter lane.

Answer: Yes.

12. Whether the existing Anthropic adapter should be treated as general adapter
    authorization.

Answer: No.

13. Whether the existing Anthropic adapter should be treated as general runtime
    authority.

Answer: No.

14. Whether the existing Anthropic adapter should be treated as general
    execution capability.

Answer: No.

15. Whether the existing Anthropic adapter should be treated as authorization
    for new adapter implementation.

Answer: No.

16. Whether the existing Anthropic adapter should be treated as authorization
    for external tool control.

Answer: No.

17. Whether the existing Anthropic adapter should be treated as authorization
    for Business Delivery OS, Personal AI Execution OS, Creative Production OS,
    or Research Decision OS.

Answer: No.

18. Whether opt-in live tests, if present, make the adapter generally
    executable in default CI.

Answer: No.

19. Whether opt-in live tests, if present, should be classified as opt-in
    real-provider ignition proof only.

Answer: Yes.

20. Whether the existing adapter baseline creates a conflict with the previous
    marker-only assumption that `kernel/adapters/` is empty / marker-only.

Answer: Yes.

21. Whether future marker files may proceed under the old hard-fail rule that
    no `.py` or `__init__.py` may exist anywhere under `kernel/adapters`.

Answer: No.

22. Whether future marker files may proceed only after choosing a reconciliation
    strategy.

Answer: Yes.

23. Whether the recommended strategy is to preserve the existing adapter lane
    and relocate non-runtime marker files outside `kernel/adapters`.

Answer: Yes, unless Codex finds exact evidence that another option is safer.
No exact evidence was found that another option is safer.

24. Whether deleting the existing adapter files is authorized by this audit.

Answer: No.

25. Whether moving the existing adapter files is authorized by this audit.

Answer: No.

26. Whether modifying the existing adapter files is authorized by this audit.

Answer: No.

27. Whether actual adapter implementation is authorized by this audit.

Answer: No.

28. Whether runtime authority or execution capability is authorized by this
    audit.

Answer: No.

29. Whether service calls, DB/UoW, evidence/audit append, executor, restore,
    subprocess, network, external tool control, tool execution, broad I/O,
    durable writes, or irreversible actions are authorized by this audit.

Answer: No.

30. Whether any concrete repository defect exists.

Answer: Yes: the previous marker-only path treated `kernel/adapters/` as
marker-only, but the authoritative baseline already contains a real Python
adapter lane.

31. Whether that defect requires deleting existing adapter code.

Answer: No.

32. Whether that defect requires classifying the existing adapter baseline
    before retrying marker files.

Answer: Yes.

## Reconciliation Options

Option 1: Preserve existing adapter lane and relocate marker files outside
`kernel/adapters/`.

Evaluation: This option preserves the authoritative baseline, avoids deleting,
moving, or modifying existing adapter files, and prevents future non-runtime
marker files from pretending `kernel/adapters/` is empty or marker-only.

Decision: Recommended.

Option 2: Preserve existing adapter lane and allow marker files under
`kernel/adapters/` with a rewritten "no new Python files" rule.

Evaluation: This option may be possible later, but it keeps marker artifacts in
a directory that already contains actual adapter code. That increases ambiguity
between non-runtime marker content and pre-existing real-model adapter code.

Decision: Not recommended by this audit.

Option 3: Delete existing adapter lane through a separate deletion audit.

Evaluation: This audit found no authorization to delete
`kernel/adapters/__init__.py` or `kernel/adapters/anthropic_adapter.py`. A
deletion path would require a separate explicit deletion audit.

Decision: Not authorized by this audit.

Option 4: Move existing adapter lane through a separate migration audit.

Evaluation: This audit found no authorization to move the existing adapter lane.
A migration path would require a separate explicit migration audit.

Decision: Not authorized by this audit.

Option 5: Pause all marker work.

Evaluation: Pausing remains available if later evidence proves relocation
unsafe, but this audit found no concrete defect that requires a full pause
instead of preserving the existing lane and relocating future marker files.

Decision: Not recommended by this audit.

## Recommendation

Recommended strategy:

- Preserve existing adapter lane and relocate marker files outside
  `kernel/adapters/`.

Required future marker path if this recommendation is used:

- `docs/markers/adapters/narrow/`

Required future marker files if this recommendation is used:

- `docs/markers/adapters/narrow/README.md`
- `docs/markers/adapters/narrow/contract_notes.md`
- `docs/markers/adapters/narrow/non_authority.md`
- `docs/markers/adapters/narrow/forbidden_operations.md`
- `docs/markers/adapters/narrow/future_gate.md`

Next package recommended:

- `relocated-non-runtime-adapter-markers-decision-audit-v1`

## Marker Path Consequence

Because `kernel/adapters/` already contains real Python adapter code, future
non-runtime marker files must not assume that `kernel/adapters/` is empty or
marker-only.

Recommended future marker root:

`docs/markers/adapters/narrow/`

The previous `non-runtime-adapter-skeleton-markers-v1` package must not be
retried unchanged.

## Verdict Options

Allowed verdict options:

- `CLASSIFY_EXISTING_ADAPTER_BASELINE_RELOCATE_MARKERS_NEXT`
- `CLASSIFY_EXISTING_ADAPTER_BASELINE_REWRITE_MARKER_RULE_NEXT`
- `CLASSIFY_EXISTING_ADAPTER_BASELINE_DELETE_AUDIT_NEXT`
- `CLASSIFY_EXISTING_ADAPTER_BASELINE_MOVE_AUDIT_NEXT`
- `CLASSIFY_EXISTING_ADAPTER_BASELINE_PAUSE_MARKERS`
- `BLOCKED_BY_CONCRETE_REPOSITORY_DEFECTS`

Verdict:

- `CLASSIFY_EXISTING_ADAPTER_BASELINE_RELOCATE_MARKERS_NEXT`

## Boundary Confirmation

Production code changed: No.
Tests changed: No.
Acceptance tests changed: No.
Examples changed: No.
Examples code changed: No.
README.md changed: No.
docs/current_phase.md changed: No.
Public overview changed: No.
Dry-run manifest fixture changed: No.
Dry-run manifest fixture usage doc changed: No.
Lifecycle changed: No.
Replay verifier changed: No.
Controlled demo changed: No.
Narrow adapter contract changed: No.
Narrow adapter skeleton design changed: No.
Existing adapter file deleted: No.
Existing adapter file moved: No.
Existing adapter file modified: No.
Adapter implementation added: No.
Runtime adapter implementation added: No.
Adapter code added: No.
Adapter interface code added: No.
Adapter skeleton code added: No.
Python files added: No.
`__init__.py` added: No.
Python modules added: No.
Python packages added: No.
Python classes added: No.
Dataclasses added: No.
Protocols added: No.
Schemas added: No.
Validators added: No.
Tests added: No.
Runtime functions added: No.
Runtime authority introduced: No.
Execution capability introduced: No.
CLI added: No.
Repository calls introduced: No.
Service calls introduced: No.
DB/repository/UoW introduced: No.
Evidence/audit append introduced: No.
Executor introduced: No.
Executor hooks introduced: No.
Restore service introduced: No.
Subprocess introduced: No.
Network introduced: No.
External tool control introduced: No.
Tool execution introduced: No.
Multi-file lifecycle introduced: No.
Broad physical I/O introduced: No.
Durable writes introduced: No.
Irreversible actions introduced: No.
New governance boundary family introduced: No.
Business / Personal / Creative / Research OS introduced: No.
