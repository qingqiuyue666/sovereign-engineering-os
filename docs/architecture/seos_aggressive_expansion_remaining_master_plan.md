# SEOS Aggressive Expansion Remaining Master Plan

## Architecture Mode

**Architecture Override: Aggressive Expansion**

SEOS is being advanced from a passive audit gateway into an active local AI/VFX execution and recovery kernel.

The system target is:

```text
JSON-RPC Control Plane
→ Runtime Token / Policy Gate
→ Concurrent DCC Adapter Kernel
→ Auto-Provisioning Layer
→ Cross-Software Workflow Engine
→ State-Code Error Convergence
→ Patch-Oriented Self-Healing Loop
→ Project / Asset / Shot Runtime
→ Output Packaging
→ Operator Surface
→ Skills
→ Multimodal Review
→ Pattern Assimilation
→ Real Production Dogfood
```

This plan replaces the previous conservative remaining-work plan.

The core implementation posture is:

```text
Build execution infrastructure first.
Automate preflight recovery.
Run adapters concurrently.
Use receipts and state ledgers as runtime substrate, not bureaucracy.
Move fast through controlled JSON-RPC methods.
```

---

# 0. Current Reported Baseline

The local cloned repo already has:

- `docs/architecture/seos_complete_kernel_pivot_master_plan.md`
- canonical schemas under `schemas/`
- JSON-RPC kernel:
  - gateway
  - runtime token policy
  - adapter registry
  - artifact manifests
  - receipts
  - failure bundles
  - state ledger
- CLI wiring through `apps/operator_cli/main.py`
- milestone payload:
  - `examples/rpc/cross_dcc_probe.json`
- focused tests:
  - `tests/tracer_bullet/test_seos_rpc_kernel_pivot_v1.py`
- focused validation reportedly passed:
  - fake DCC adapter tests
  - Houdini adapter contract tests
  - SEOS RPC kernel pivot tests
- `python3 seos.py rpc invoke examples/rpc/cross_dcc_probe.json --json` reportedly exits `0`
- local observed result:
  - Houdini probe succeeded
  - ComfyUI unavailable
  - DaVinci dependency-blocked
  - workflow terminal status `FAILED` by fail-closed semantics
- no commit or push yet

This baseline is now treated as:

```text
KERNEL_SKELETON_LOCAL_READY
```

The next objective is:

```text
MAINLINE_KERNEL_COMMIT
→ AUTO_PROVISIONING_ADAPTERS
→ CONCURRENT_MULTI_DCC_EXECUTION
→ CROSS_SOFTWARE_WORKFLOW
→ STATE_CODE_SELF_HEALING
```

---

# 1. Global Engineering Contract

## 1.1 Execution entry

All runtime actions enter through:

```text
JSON-RPC envelope
→ schema validation
→ runtime token / policy verification
→ adapter dispatch
→ state ledger
→ artifact receipt / failure bundle
```

## 1.2 Runtime token

Runtime tokens are machine-issued grants.

Tokens define:

- allowed methods
- allowed adapters
- allowed actions
- allowed output roots
- max timeout
- max concurrency
- auto-provision permission
- retry budget
- patch-generation permission
- patch-application mode
- external pattern assimilation mode

## 1.3 Adapter method boundary

Every DCC adapter implements:

```python
detect()
preflight()
auto_provision()
execute()
collect_outputs()
classify_failure()
repair_hint()
```

## 1.4 State machine

Canonical states:

```text
CREATED
VALIDATING
QUEUED
PREFLIGHTING
PROVISIONING
READY
RUNNING
COLLECTING
SUCCEEDED
FAILED
RETRYING
PATCHING
RERUNNING
PACKAGING
TERMINAL_SUCCEEDED
TERMINAL_FAILED
```

## 1.5 Failure codes

Canonical failure codes:

```text
SCHEMA_INVALID
TOKEN_INVALID
TOKEN_EXPIRED
METHOD_NOT_ALLOWED
ADAPTER_NOT_FOUND
ADAPTER_UNAVAILABLE
AUTO_PROVISION_FAILED
PREFLIGHT_FAILED
EXECUTION_FAILED
PROCESS_EXIT_NONZERO
TIMEOUT
OUTPUT_MISSING
OUTPUT_INVALID
ARTIFACT_HASH_FAILED
DEPENDENCY_BLOCKED
SERVICE_UNAVAILABLE
PATCH_GENERATION_FAILED
PATCH_APPLY_FAILED
PATCH_TEST_FAILED
STATE_WRITE_FAILED
```

---

# 2. Step 1 — Mainline Kernel Commit and Push

## Goal

Merge validation and commit flow into a single operator-owned mainline action.

## Actions

Run:

```bash
git status --short
git diff --stat
python3 -m unittest tests.tracer_bullet.test_fake_dcc_adapter_v1 tests.tracer_bullet.test_houdini_adapter_contract_v1 tests.tracer_bullet.test_seos_rpc_kernel_pivot_v1 -v
python3 scripts/identity_boundary_check_v1.py
python3 scripts/creative_total_check_v3.py
make ci
git diff --check
python3 seos.py rpc invoke examples/rpc/cross_dcc_probe.json --json
```

Inspect generated ledger/manifests/receipts/failure bundles.

Then commit and push:

```bash
git add docs/architecture/seos_complete_kernel_pivot_master_plan.md schemas seos apps/operator_cli/main.py examples/rpc tests/tracer_bullet/test_seos_rpc_kernel_pivot_v1.py
git commit -m "kernel pivot"
git push
```

## Commit discipline

Commit only:

- source files
- schemas
- docs
- examples
- tests
- intentional fixture outputs

Do not commit accidental run outputs unless intentionally stored as fixtures.

## Acceptance

- full repo validation passes
- kernel pivot committed
- branch pushed
- working tree clean after push

---

# 3. Step 2 — Runtime Token Policy Upgrade

## Goal

Extend runtime tokens from passive validation into active execution policy.

## New token fields

```json
{
  "auto_provision": {
    "enabled": true,
    "allowed_adapters": ["comfyui_local", "davinci_resolve"],
    "max_wait_seconds": 90,
    "heartbeat_interval_seconds": 3
  },
  "concurrency": {
    "max_global_jobs": 3,
    "max_per_adapter_jobs": {
      "houdini_hython": 1,
      "comfyui_local": 2,
      "davinci_resolve": 1
    }
  },
  "retry": {
    "enabled": true,
    "max_attempts": 2,
    "backoff_seconds": 5
  },
  "patch_repair": {
    "enabled": true,
    "mode": "generate_patch_then_test",
    "allowed_tools": ["cline", "aider"],
    "auto_apply": false
  }
}
```

## Required modules

```text
seos/runtime/token_policy.py
seos/runtime/concurrency.py
seos/runtime/retry_budget.py
seos/runtime/patch_repair_policy.py
```

## Acceptance

- tokens can express auto-provision permission
- tokens can express concurrency budgets
- tokens can express retry budgets
- tokens can express patch-generation mode
- gateway rejects actions outside token policy

---

# 4. Step 3 — Auto-Provisioning Layer

## Goal

Adapters must attempt local service/app startup when preflight fails due to missing running service or app process.

## Core interface

```python
class DCCAdapter:
    def auto_provision(self, intent, policy) -> ProvisionResult:
        ...
```

## Provision result

```json
{
  "adapter": "comfyui_local",
  "status": "PROVISIONED",
  "method": "launch_command",
  "pid": 1234,
  "heartbeat_status": "READY",
  "elapsed_ms": 8421
}
```

## ComfyUI auto-provision

Trigger when:

```text
service_probe cannot connect to base_url
```

Provision methods:

1. use configured launch command
2. use configured working directory
3. wait for `/system_stats` or equivalent heartbeat
4. retry until `max_wait_seconds`

Configuration file:

```text
config/local_adapters/comfyui_local.json
```

Example:

```json
{
  "adapter": "comfyui_local",
  "base_url": "http://127.0.0.1:8188",
  "launch_command": ["python3", "main.py", "--listen", "127.0.0.1", "--port", "8188"],
  "working_dir": "/absolute/path/to/ComfyUI",
  "heartbeat_path": "/system_stats",
  "startup_timeout_seconds": 90
}
```

## DaVinci auto-provision

Trigger when:

```text
DaVinci Resolve scripting API cannot attach because app is not running
```

Provision methods on macOS:

```text
open -a "DaVinci Resolve"
```

Then wait for Python API availability.

Configuration file:

```text
config/local_adapters/davinci_resolve.json
```

Example:

```json
{
  "adapter": "davinci_resolve",
  "app_name": "DaVinci Resolve",
  "startup_command": ["open", "-a", "DaVinci Resolve"],
  "startup_timeout_seconds": 120,
  "api_probe_script": "seos/adapters/davinci/scripts/probe_api.py"
}
```

## Houdini auto-provision

Houdini hython does not need app startup for headless subprocess mode.

Provision is limited to:

```text
resolve executable path
verify executable exists
verify version probe
```

## Acceptance

- ComfyUI unavailable can trigger auto-provision if token allows it
- DaVinci unavailable can trigger app launch if token allows it
- provision events are written to state ledger
- provision failure becomes `AUTO_PROVISION_FAILED`
- successful provision proceeds to execute

---

# 5. Step 4 — Concurrent Adapter Implementation

## Goal

Implement Houdini, ComfyUI, and DaVinci as same-level adapters.

## 5.1 HoudiniHythonAdapter

Actions:

```text
version_probe
smoke_cache_test
geometry_cache_test
hip_open_validate
```

Execution:

```text
hython subprocess
→ repo-owned script_id
→ structured runtime payload
→ output root
→ manifest/receipt
```

Output refs:

```text
.bgeo.sc
.exr
.json
.log
```

## 5.2 ComfyUILocalAdapter

Actions:

```text
service_probe
submit_workflow
poll_history
collect_outputs
```

Execution:

```text
auto_provision if service unavailable
→ POST /prompt
→ poll /history/{prompt_id}
→ collect /view outputs
→ copy or reference collected outputs
→ hash receipt
```

Transport:

```text
HTTP
WebSocket optional
```

## 5.3 DaVinciResolveAdapter

Actions:

```text
version_probe
project_probe
timeline_export_probe
render_preset_test
```

Execution:

```text
auto_provision app if not running
→ attach local scripting API
→ run probe/export/render preset
→ collect outputs
→ hash receipt
```

## Acceptance

- all three adapters use the same base interface
- all three support detect/preflight/auto_provision/execute/collect_outputs/classify_failure
- missing tools or failed startup produce standard state transitions
- adapter results are normalized
- gateway dispatch handles all three adapters

---

# 6. Step 5 — Run Queue and Bounded Concurrency

## Goal

Move from single invoke to concurrent execution.

## Build

```text
seos/runtime/run_queue.py
seos/runtime/job_lock.py
seos/runtime/worker_pool.py
seos/runtime/concurrency_ledger.py
```

## Requirements

- global concurrency budget
- per-adapter concurrency budget
- run queue
- run state updates
- job cancellation request
- timeout handling
- adapter process tracking
- workflow node scheduling

## CLI

```bash
python3 seos.py rpc enqueue examples/rpc/cross_dcc_probe.json
python3 seos.py run list
python3 seos.py run inspect <run_id>
python3 seos.py run cancel <run_id>
```

## Acceptance

- multiple jobs can queue
- concurrency limits enforced
- Houdini limited to one job if configured
- ComfyUI can run more than one if configured
- cancellations and timeouts write state transitions

---

# 7. Step 6 — Shared Memory / Zero-Copy Cache Reference Model

## Goal

Prevent wasteful copying across DCC workflow nodes.

## Principle

Large artifacts are passed by reference, not duplicated.

## ArtifactRef V1

```json
{
  "schema_version": "seos.artifact_ref.v1",
  "artifact_id": "art_...",
  "producer_run_id": "run_...",
  "producer_node_id": "n1",
  "uri": "file:///absolute/or/local-managed/path/cache/frame_0001.bgeo.sc",
  "relative_path": "cache/frame_0001.bgeo.sc",
  "size_bytes": 123456,
  "sha256": "...",
  "media_type": "application/x-bgeo-sc",
  "storage_mode": "path_ref",
  "copy_policy": "zero_copy_reference",
  "lifetime": "managed_by_run_package"
}
```

## Cache routing

Workflow nodes consume:

```text
ArtifactRef
```

not raw file copies.

## Supported storage modes

```text
path_ref
memory_mapped_ref
managed_copy
external_ref
```

Phase default:

```text
path_ref
```

Future advanced mode:

```text
memory_mapped_ref
```

## Acceptance

- Houdini output artifacts are represented as ArtifactRef
- ComfyUI and DaVinci nodes can consume ArtifactRef metadata
- no duplicate copy unless node explicitly requests `managed_copy`
- receipt records artifact reference and hash

---

# 8. Step 7 — Cross-Software Workflow Engine

## Goal

Execute workflows across Houdini, ComfyUI, and DaVinci.

## Workflow example

```text
houdini_hython.smoke_cache_test
→ artifact.collect
→ comfyui_local.submit_workflow
→ artifact.collect
→ davinci_resolve.project_probe
→ package.write
```

## Required engine modules

```text
seos/workflows/definition.py
seos/workflows/node.py
seos/workflows/edge.py
seos/workflows/runner.py
seos/workflows/scheduler.py
seos/workflows/artifact_router.py
seos/workflows/rerun.py
```

## Engine requirements

- topological scheduling
- bounded parallelism
- per-node adapter dispatch
- ArtifactRef handoff
- zero-copy default
- node-level receipts
- workflow-level receipt
- failure propagation
- rerun from failed node

## Acceptance

- workflow can chain all three adapters
- node outputs become ArtifactRefs
- dependent nodes receive ArtifactRefs
- workflow stops or retries based on error policy
- workflow summary is deterministic

---

# 9. Step 8 — Agentic Routing and Code-Level Self-Healing

## Goal

Convert failure bundles into patch-generation loops when the failure is code-level and locally repairable.

## Trigger conditions

Patch repair may trigger when:

```text
failure_code == EXECUTION_FAILED
or failure_code == PROCESS_EXIT_NONZERO
or failure_code == SCHEMA_INVALID
or failure_code == OUTPUT_INVALID
```

and FailureBundle contains:

```text
Python traceback
schema validation stack
adapter module path
test command
reproduction command
```

## PatchRepairJob V1

```json
{
  "schema_version": "seos.patch_repair_job.v1",
  "repair_id": "repair_...",
  "source_failure_bundle": "...",
  "target_files": [],
  "reproduction_command": "...",
  "test_commands": [],
  "allowed_tools": ["cline", "aider"],
  "mode": "generate_patch_then_test",
  "auto_apply": false,
  "max_iterations": 2
}
```

## Repair flow

```text
failure bundle
→ classify as code-level repairable
→ build patch repair prompt
→ call local patch tool
→ generate patch
→ apply patch if policy allows
→ run reproduction command
→ run test commands
→ update repair ledger
→ rerun workflow node
```

## Required modules

```text
seos/repair/classifier.py
seos/repair/patch_job.py
seos/repair/local_model_bridge.py
seos/repair/patch_apply.py
seos/repair/repair_ledger.py
```

## Acceptance

- tracebacks become structured repair jobs
- patch generation can be invoked through local configured tool
- patch application is policy-controlled
- tests run after patch
- failed patch attempts write repair failure bundle
- successful patch attempts rerun the failed node

---

# 10. Step 9 — Project / Asset / Shot Runtime

## Goal

Attach execution to production objects.

## Models

```text
Project
Asset
Shot
Task
Artifact
Version
ReviewNote
Package
```

## CLI

```bash
python3 seos.py project create <name>
python3 seos.py asset scan <root>
python3 seos.py shot create <project_id> <shot_name>
python3 seos.py shot attach-workflow <shot_id> <workflow_id>
python3 seos.py shot run <shot_id>
```

## Requirements

- assets scan into registry
- shots reference assets
- workflows attach to shots
- artifacts attach to workflow nodes
- receipts attach to shot runs
- package attaches to shot version

## Acceptance

- one shot can run a cross-DCC workflow
- run outputs are traceable to shot and project
- package can include all receipts and ArtifactRefs

---

# 11. Step 10 — Output Packaging

## Goal

Produce portable shot/run packages.

## Commands

```bash
python3 seos.py package run <run_id>
python3 seos.py package shot <shot_id>
```

## Package contents

```text
manifest.json
workflow_definition.json
workflow_receipt.json
node_receipts/
failure_bundles/
artifact_manifest.json
artifact_refs.json
stdout_stderr_hashes.json
review_notes.md
```

## Package modes

```text
manifest_only
managed_copy
full_package
```

Default:

```text
manifest_only
```

## Acceptance

- package can be generated from run
- package can be generated from shot
- manifest mode references large assets by ArtifactRef
- managed copy mode copies selected artifacts into package root

---

# 12. Step 11 — Local Operator Dashboard

## Goal

Expose runtime state and workflow operations.

## Views

```text
Runs
Queue
Adapters
Workflows
Artifacts
Failures
Repairs
Projects
Shots
Packages
```

## Dashboard authority

Can:

```text
read state ledger
inspect receipts
inspect failure bundles
submit predefined JSON-RPC templates
enqueue predefined workflows
show repair jobs
```

Must use existing gateway methods.

## Acceptance

- dashboard reads state
- dashboard submits predefined RPC templates
- dashboard shows live run status
- dashboard does not invent adapter actions

---

# 13. Step 12 — Skill System

## Goal

Package repeatable execution workflows.

## Skill layout

```text
skills/<skill_name>/
  skill.yaml
  schemas/
  rpc_templates/
  workflows/
  prompts/
  tests/
  runbook.md
```

## Initial skills

```text
houdini_smoke_cache
comfyui_empty_image
davinci_project_probe
cross_dcc_probe
shot_package
failure_convergence
patch_repair
```

## Acceptance

- skills register JSON-RPC templates
- skills register workflow definitions
- skills define required adapters
- skills define output artifact expectations
- skills cannot bypass gateway

---

# 14. Step 13 — Multimodal Review Layer

## Goal

Use visual outputs as reviewable artifacts.

## Artifacts

```text
visual_review.json
visual_review.md
reference_compare.json
quality_failure_bundle.json
```

## Review categories

```text
composition
lighting
material_quality
motion_readability
color_consistency
render_artifacts
```

## Flow

```text
output artifact refs
→ frame extraction where needed
→ visual review job
→ review artifact
→ suggested workflow update
```

## Acceptance

- visual review attaches to shot/package
- review can mark output as accepted/rejected
- rejected output can route to repair or rerun workflow

---

# 15. Step 14 — GitHub Pattern Assimilator

## Goal

Accelerate architecture extraction from mature repositories.

## Modes

```text
report_only
pattern_extract
implementation_mapping
controlled_import
```

## Outputs

```text
pattern_report.md
seos_mapping.json
risk_report.md
implementation_plan.md
candidate_patch_plan.md
```

## Initial source classes

```text
ComfyUI-style workflow graphs
OpenHands-style runtime state
MCP-style tool schemas
VFX pipeline asset/shot models
DCC adapter examples
dashboard patterns
```

## Acceptance

- assimilator can produce architecture reports
- mapping can generate implementation tasks
- controlled import mode produces candidate patches for review/test
- imported patterns are tracked in ledger

---

# 16. Step 15 — Real Production Dogfood

## Goal

Use SEOS on real AI/VFX production-style shots.

## Dogfood shots

```text
energy impact
sword slash
smoke burst
portal/lightning
Houdini cache + ComfyUI output
ComfyUI output + DaVinci handoff
```

## Required per shot

```text
project record
shot record
asset refs
workflow definition
adapter receipts
artifact manifests
failure bundles
repair jobs
package
review notes
rerun history
```

## Acceptance

- at least 3 shot workflows execute through available adapters
- failures are handled by convergence loop
- packages are generated
- outputs can be reviewed
- repeatable templates are extracted

---

# 17. Immediate Codex/Cline Task Order

Use this exact order.

## Task 1

Overwrite the current remaining-work file with this aggressive expansion plan.

## Task 2

Run validation and commit/push kernel skeleton.

## Task 3

Implement runtime token policy upgrade.

## Task 4

Implement auto-provisioning layer.

## Task 5

Implement concurrent adapter kernel for Houdini, ComfyUI, DaVinci.

## Task 6

Implement run queue and concurrency budget.

## Task 7

Implement ArtifactRef / zero-copy path reference model.

## Task 8

Implement cross-software workflow engine.

## Task 9

Implement error convergence and retry policy.

## Task 10

Implement code-level patch repair loop.

## Task 11

Implement project/asset/shot runtime.

## Task 12

Implement output packaging.

## Task 13

Implement dashboard.

## Task 14

Implement skill system.

## Task 15

Implement multimodal review.

## Task 16

Implement GitHub pattern assimilator.

## Task 17

Run real production dogfood shots.

---

# 18. Final Completion Definition

The system is functionally successful when:

```text
python3 seos.py shot run <shot_id>
```

can route a shot through available local adapters, auto-provision missing local services where configured, execute workflow nodes concurrently within budget, pass large artifacts by reference, hash outputs, converge failures, generate repair jobs when code-level failures occur, package the result, and attach review artifacts to the shot record.

The first hard production milestone is:

```text
Houdini hython
→ ComfyUI local
→ DaVinci local API
```

with:

```text
state ledger
ArtifactRefs
receipts
failure bundles
retry records
package manifest
```
