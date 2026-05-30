# Local Asset Next Bounded Smoke Cycle Contract From Run Promotion Gate v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`<repo-root>`

Branch:
`feat/local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate-v1`

## Objective

Add a non-executing cycle-contract generator that consumes only a ready next
bounded smoke iteration run promotion gate and emits the next bounded smoke
cycle contract artifact. The contract is still not production approval. It
packages the approved bounded run for a later human review/admission step.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate(...)`,
the launcher
`run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_launcher(...)`,
the CLI command
`launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate`,
and task graph support for capability
`launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate`.

Required builder inputs are `run_promotion_gate_output_dir`, `output_dir`, and
`cycle_contract_id`. Optional metadata is `project_id`, `reviewer_id`, and
`operator_notes`.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate \
  --run-promotion-gate-output-dir /path/to/run-promotion-gate-output \
  --output-dir /path/to/next-cycle-contract-output \
  --cycle-contract-id next-cycle-contract-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

## Schema

The contract JSON uses `contract_type:
local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_v1`,
`authority: non_authority_bounded_cycle_contract_record`, and
`execution_capability:
local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_only`.

It records contract metadata, inherited review packet/runner/request/run
facts, source gate status/decision/action, contract status, contract decision,
next allowed action, cycle contract creation, source artifact refs,
missing/untrusted artifacts, contract blockers, disallowed actions,
deterministic ordering, human approval/review requirements, and explicit false
boundary flags.

The manifest uses `manifest_type:
local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest_v1`
and binds the contract, summary, checklist, source artifact refs, contract
status, contract decision, next allowed action, cycle contract creation, and
explicit false contract boundary flags.

## Source Artifact Policy

The contract reads only generated run promotion gate artifacts by explicit
filename from `run_promotion_gate_output_dir`. It does not recursively index
that directory, run review packet output, runner output, actual iteration
output, or candidate input files.

Required source artifacts:

- `local_asset_next_bounded_smoke_iteration_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional source artifacts:

- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md`

Malformed JSON, source artifact symlinks, type mismatches, missing required
source artifacts, and hash mismatches block. The promotion gate manifest must
hash-bind the source gate and optional summary/checklist when present. The
artifact index manifest must hash-bind the source artifact index.

## Required Artifacts

The output directory must already exist. It receives:

- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed on existing files or symlink
collisions at expected output paths.

## Readiness Rules

The contract is ready only when the source gate reports:

- `gate_status =
  next_bounded_smoke_iteration_run_promotion_gate_ready`
- `gate_decision =
  approve_next_bounded_smoke_iteration_run_for_cycle_contract`
- `next_allowed_action =
  create_next_bounded_smoke_cycle_contract_from_run`
- `bounded_run_promotion_approved=true`
- `cycle_contract_generation_allowed=true`
- `cycle_contract_generated=false`
- source production scan, production promotion, automatic approval, autonomy,
  runner re-execution, candidate access, mutation, media organizer, output
  overwrite, network, model, external runtime, and production scan
  recommendation flags are explicitly boolean false
- `required_human_approval=true`
- `required_human_review=true`
- `gate_blockers`, `missing_required_artifacts`, and `untrusted_artifacts` are
  empty
- deterministic ordering is true

Inherited run facts must be valid metadata-only facts: review/runner/request
identifiers and paths are non-empty strings; limits are objects; candidate
file count, total bytes, and max depth are non-negative integers; candidate
symlink metadata is empty when present; and bounded file records are sorted by
`relative_path` and contain no raw content fields.

## Cycle-Contract-Only Rule

When ready, the contract sets `contract_status =
next_bounded_smoke_cycle_contract_ready`, `contract_decision =
create_bounded_smoke_cycle_contract_from_approved_run`, and
`next_allowed_action =
submit_next_bounded_smoke_cycle_contract_for_human_review`.

It does not create a production gate, approve production scanning, grant
production promotion, execute a runner, regenerate a run review packet, or
re-execute the run promotion gate.

## Source Boundary Boolean Fail-Closed Policy

Missing or non-boolean required source safety fields block with
`blocked_invalid_source_gate_record`. Required source boundary booleans set to
unsafe values block with `blocked_source_boundary_violation`.

## Blocker Logic

Missing required generated artifacts produce
`blocked_missing_required_artifacts`. Untrusted generated artifacts produce
`blocked_untrusted_artifacts`. A non-ready source gate produces
`blocked_source_gate_not_ready`. Malformed source gate fields produce
`blocked_invalid_source_gate_record`. Source boundary violations produce
`blocked_source_boundary_violation`. Invalid inherited run facts produce
`blocked_invalid_inherited_run_facts`. Source gate blockers, missing required
artifacts, or untrusted artifacts produce
`blocked_source_gate_contains_blockers`. Invalid contract metadata produces
`blocked_invalid_cycle_contract_metadata`.

## Generated-Artifacts-Only Policy

The contract never scans, stats, lists, reads, or hashes live candidate
inputs. Candidate paths and bounded file records are consumed only as metadata
already present in the generated source gate.

## Artifact Index Relationship

The local output `artifact_index.json` binds only the cycle contract,
manifest, summary, and checklist. The index manifest binds that artifact
index. It does not recursively index source directories or candidate inputs.

## Task Graph Relationship

The local asset adapter registry admits
`launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate`.
Task graph execution records the contract artifact paths, contract status,
contract decision, next allowed action, source gate readiness metadata,
inherited metadata, human approval/review requirements, and explicit false
boundary flags. Task graph artifact output binding adds the four cycle
contract-from-run-gate roles.

## Failure Behavior

If `output_dir` is missing, unsafe, overlapping with the source directory, or
already contains expected output files, the builder returns a structured
failure and writes no artifacts. If the source promotion gate directory is
missing or unsafe while `output_dir` is safe, it writes a blocked contract
artifact without creating or mutating source directories.

## Deterministic Ordering

Source artifacts are sorted by role. Bounded file records must already be
sorted by `relative_path`. Checklist items, disallowed actions, source
artifact roles, and artifact index entries are emitted in stable order.

## Explicit Non-Behavior

This branch does not run production scan, create a production gate, grant
production promotion, execute a runner, regenerate a run review packet,
re-execute a run promotion gate, read live candidate files, list live
candidate directories, hash live candidate input files, mutate upstream
outputs, move/rename/delete files, deduplicate files, copy raw private
content, add media organizer behavior, use network access, call model APIs,
invoke external runtimes, add UI, add Operator Console behavior, add
watcher/daemon behavior, grant automatic approval, or grant autonomous
execution.

## Validation Commands

Required validation for this branch includes:

```bash
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate

python3 -m unittest \
  tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_run_promotion_gate \
  tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_run_review_packet \
  tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner \
  tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner_admission \
  tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_contract \
  tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_human_review

python3 -m unittest \
  tests.personal_ai.test_adapter_registry \
  tests.personal_ai.test_product_health_check \
  tests.personal_ai.test_task_graph \
  tests.tracer_bullet.test_task_graph_artifact_output_binding \
  tests.tracer_bullet.test_task_graph_local_asset_scan_node

python3 -m unittest discover tests

make ci

git diff --check
```
