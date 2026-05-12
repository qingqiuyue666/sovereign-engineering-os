# Relocated Non-Runtime Adapter Markers Decision Audit V1

## Scope

This is a narrow docs-only decision audit for whether the next package may
create relocated non-runtime adapter marker files under
`docs/markers/adapters/narrow/` instead of `kernel/adapters/`.

This is a decision audit only.

This is not marker creation.
This is not adapter implementation.
This is not runtime adapter implementation.
This is not adapter code.
This is not adapter interface code.
This is not adapter skeleton code.
This is not Python files.
This is not __init__.py.
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

This audit does not create marker files. This audit does not create
`docs/markers/adapters/narrow/README.md`. This audit does not create
`docs/markers/adapters/narrow/contract_notes.md`. This audit does not create
`docs/markers/adapters/narrow/non_authority.md`. This audit does not create
`docs/markers/adapters/narrow/forbidden_operations.md`. This audit does not
create `docs/markers/adapters/narrow/future_gate.md`.

This audit does not delete files. This audit does not move files. This audit
does not modify production code. This audit does not modify tests. This audit
does not modify acceptance tests. This audit does not modify examples. This
audit does not modify examples code. This audit does not modify README.md. This
audit does not modify docs/current_phase.md. This audit does not modify the
public overview document. This audit does not modify the dry-run manifest
fixture. This audit does not modify the dry-run manifest fixture usage doc. This
audit does not modify the lifecycle implementation. This audit does not modify
the replay verifier. This audit does not modify the controlled demo. This audit
does not modify the narrow adapter contract document. This audit does not modify
the narrow adapter skeleton design document.

This audit does not modify `kernel/adapters/__init__.py`. This audit does not
modify `kernel/adapters/anthropic_adapter.py`. This audit does not create files
under `kernel/adapters/`.

This audit does not implement adapter. This audit does not add runtime adapter
implementation. This audit does not add adapter code. This audit does not add
adapter interface code. This audit does not add adapter skeleton code. This
audit does not add Python files. This audit does not add `__init__.py`. This
audit does not add Python modules. This audit does not add Python packages. This
audit does not add Python classes, dataclasses, protocols, schemas, validators,
tests, runtime functions, CLI commands, repository calls, service calls, or
executor hooks. This audit does not add runtime. This audit does not add runtime
authority. This audit does not add execution capability. This audit does not add
executor. This audit does not add DB/repository/UoW. This audit does not add
evidence/audit append. This audit does not add restore service. This audit does
not add subprocess. This audit does not add network. This audit does not add
tool execution. This audit does not add external tool control. This audit does
not add multi-file lifecycle. This audit does not add broad physical I/O. This
audit does not add durable writes. This audit does not add irreversible actions.

This audit does not start Business Delivery OS, Personal AI Execution OS,
Creative Production OS, or Research Decision OS.

## Checkpoint Basis

Current required checkpoint:

- `existing-adapter-baseline-classification-audit-v1`

Authoritative `origin/main` HEAD verified before this branch:

- `2ad76673ceae1976aa82574e243ec503098b03c0`

Required prior classification:

- `PRE_EXISTING_PHASE1_REAL_MODEL_IGNITION_ADAPTER_LANE`

Required prior classification verdict:

- `CLASSIFY_EXISTING_ADAPTER_BASELINE_RELOCATE_MARKERS_NEXT`

Required prior next package:

- `relocated-non-runtime-adapter-markers-decision-audit-v1`

Existing classified adapter baseline files:

- `kernel/adapters/__init__.py`
- `kernel/adapters/anthropic_adapter.py`

Existing related opt-in live test surfaces:

- `tests/tracer_bullet/test_real_adapter_live_ignition.py`
- `tests/tracer_bullet/test_real_fix_tracer_live.py`
- `tests/tracer_bullet/test_real_adapter_live_failure_ignition.py`

Recommended future marker root from prior audit:

- `docs/markers/adapters/narrow/`

Recommended future marker files from prior audit:

- `docs/markers/adapters/narrow/README.md`
- `docs/markers/adapters/narrow/contract_notes.md`
- `docs/markers/adapters/narrow/non_authority.md`
- `docs/markers/adapters/narrow/forbidden_operations.md`
- `docs/markers/adapters/narrow/future_gate.md`

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
- existing adapter baseline remains classified as PRE_EXISTING_PHASE1_REAL_MODEL_IGNITION_ADAPTER_LANE
- existing adapter baseline classification does not authorize new adapter implementation
- existing adapter baseline classification does not authorize runtime authority
- existing adapter baseline classification does not authorize execution capability
- existing adapter baseline classification does not authorize external tool control
- existing adapter baseline classification does not authorize Business / Personal / Creative / Research OS
- existing adapter files may not be deleted by this audit
- existing adapter files may not be moved by this audit
- existing adapter files may not be modified by this audit
- future marker files must not be created under kernel/adapters/
- future marker files must be relocated under docs/markers/adapters/narrow/
- no adapter code may be added by this audit
- no marker files may be added by this audit
- no runtime may be authorized by this audit
- no execution capability may be created by this audit
- no service call may be introduced by this audit
- no DB/UoW may be introduced by this audit
- no executor may be introduced by this audit
- no subprocess/network/tool execution may be introduced by this audit
- no external tool control may be introduced by this audit

STOP_BEFORE_ADAPTER_IMPLEMENTATION remains preserved.
Existing adapter baseline remains classified as
PRE_EXISTING_PHASE1_REAL_MODEL_IGNITION_ADAPTER_LANE.
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
Future marker files must not be created under kernel/adapters/.
Future marker files must be relocated under docs/markers/adapters/narrow/.
No adapter code may be added by this audit.
No marker files may be added by this audit.
No runtime may be authorized by this audit.
No execution capability may be created by this audit.
No service call may be introduced by this audit.
No DB/UoW may be introduced by this audit.
No executor may be introduced by this audit.
No subprocess/network/tool execution may be introduced by this audit.
No external tool control may be introduced by this audit.

## Existing Adapter Baseline

The existing adapter baseline remains classified as:

`PRE_EXISTING_PHASE1_REAL_MODEL_IGNITION_ADAPTER_LANE`

Classified baseline files:

- `kernel/adapters/__init__.py`
- `kernel/adapters/anthropic_adapter.py`

This classification preserves the existing adapter lane as a pre-existing
phase-1 real-model ignition adapter lane. It does not convert that lane into
general runtime authority, general execution capability, general adapter
authorization, external tool control, or OS-level automation authorization.

## Relocated Marker Path

Future non-runtime adapter marker files are approved only for the relocated documentation marker root:

docs/markers/adapters/narrow/

The following future files are the only approved marker candidates:

- docs/markers/adapters/narrow/README.md
- docs/markers/adapters/narrow/contract_notes.md
- docs/markers/adapters/narrow/non_authority.md
- docs/markers/adapters/narrow/forbidden_operations.md
- docs/markers/adapters/narrow/future_gate.md

No marker file is approved under kernel/adapters/.

## Reason For Relocation

kernel/adapters/ already contains a pre-existing phase-1 real-model ignition adapter lane. Relocating marker files prevents documentation-only marker artifacts from being mixed with actual Python adapter code.

## Decision Questions

1. Whether non-runtime adapter marker files should still be created under
   `kernel/adapters/`.

Answer: No.

2. Whether `kernel/adapters/` should be treated as empty or marker-only.

Answer: No.

3. Whether `kernel/adapters/` is now classified as a pre-existing phase-1
   real-model ignition adapter lane.

Answer: Yes.

4. Whether the relocated marker path should be
   `docs/markers/adapters/narrow/`.

Answer: Yes.

5. Whether the next package may create marker files under
   `docs/markers/adapters/narrow/`.

Answer: Yes, if and only if the files are Markdown-only, documentation-only,
non-runtime, non-executable marker files.

6. Whether the next package may create marker files under `kernel/adapters/`.

Answer: No.

7. Whether the next package may delete, move, or modify
   `kernel/adapters/__init__.py`.

Answer: No.

8. Whether the next package may delete, move, or modify
   `kernel/adapters/anthropic_adapter.py`.

Answer: No.

9. Whether the next package may create Python files.

Answer: No.

10. Whether the next package may create `__init__.py`.

Answer: No.

11. Whether the next package may create Python modules, Python packages, Python
    classes, dataclasses, protocols, schemas, validators, tests, runtime
    functions, CLI commands, repository calls, service calls, or executor hooks.

Answer: No.

12. Whether the next package may introduce runtime authority or execution
    capability.

Answer: No.

13. Whether the next package may introduce adapter implementation, runtime
    adapter implementation, adapter code, adapter interface code, or adapter
    skeleton code.

Answer: No.

14. Whether the next package may call services, DB/repository/UoW,
    evidence/audit append, executor, restore, CLI, subprocess, network, tool
    execution, external tool control, multi-file lifecycle, broad physical I/O,
    durable writes, or irreversible actions.

Answer: No.

15. Whether the next package may authorize external software control, including
    browser, shell, filesystem-wide mutation, DaVinci, Blender, Houdini, Unreal,
    ComfyUI, Photoshop, After Effects, or any local application.

Answer: No.

16. Whether the next package may authorize Business Delivery OS, Personal AI
    Execution OS, Creative Production OS, or Research Decision OS.

Answer: No.

17. Whether the next package may create only these files:

- `docs/markers/adapters/narrow/README.md`
- `docs/markers/adapters/narrow/contract_notes.md`
- `docs/markers/adapters/narrow/non_authority.md`
- `docs/markers/adapters/narrow/forbidden_operations.md`
- `docs/markers/adapters/narrow/future_gate.md`

Answer: Yes.

18. Whether the next package may create any additional marker files.

Answer: No.

19. Whether the next package may create any files outside
    `docs/markers/adapters/narrow/`.

Answer: No.

20. Whether the next package may change
    `docs/contracts/narrow_adapter_contract_v1.md`.

Answer: No.

21. Whether the next package may change
    `docs/design/narrow_adapter_skeleton_design_v1.md`.

Answer: No.

22. Whether any concrete repository defect blocks relocated marker decision.

Answer: No, unless Codex finds exact evidence. Codex found no exact evidence
that a concrete repository defect blocks relocated marker decision.

23. Whether the old package `non-runtime-adapter-skeleton-markers-v1` may be
    retried unchanged.

Answer: No.

24. Whether the new relocated marker package should replace the old
    `kernel/adapters` marker plan.

Answer: Yes.

## Verdict Options

Required verdict options:

- `APPROVE_RELOCATED_NON_RUNTIME_ADAPTER_MARKERS_NEXT`
- `REJECT_RELOCATED_NON_RUNTIME_ADAPTER_MARKERS_NEXT`
- `APPROVE_KERNEL_ADAPTER_MARKERS_WITH_REWRITTEN_RULE_NEXT`
- `APPROVE_EXISTING_ADAPTER_DELETION_AUDIT_NEXT`
- `APPROVE_EXISTING_ADAPTER_MIGRATION_AUDIT_NEXT`
- `BLOCKED_BY_CONCRETE_REPOSITORY_DEFECTS`

Verdict:

- `APPROVE_RELOCATED_NON_RUNTIME_ADAPTER_MARKERS_NEXT`

## Next Package

Required next package name if expected verdict is used:

- `relocated-non-runtime-adapter-markers-v1`

Required exact future files if expected verdict is used:

- `docs/markers/adapters/narrow/README.md`
- `docs/markers/adapters/narrow/contract_notes.md`
- `docs/markers/adapters/narrow/non_authority.md`
- `docs/markers/adapters/narrow/forbidden_operations.md`
- `docs/markers/adapters/narrow/future_gate.md`

This next package replaces the old `kernel/adapters` marker plan. The old
package `non-runtime-adapter-skeleton-markers-v1` must not be retried unchanged.

## Boundary Confirmation

Marker files created: No.
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
Files created under kernel/adapters: No.
Adapter implementation added: No.
Runtime adapter implementation added: No.
Adapter code added: No.
Adapter interface code added: No.
Adapter skeleton code added: No.
Python files added: No.
__init__.py added: No.
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
