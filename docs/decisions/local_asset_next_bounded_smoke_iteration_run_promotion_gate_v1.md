# Local Asset Next Bounded Smoke Iteration Run Promotion Gate v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch:
`feat/local-asset-next-bounded-smoke-iteration-run-promotion-gate-v1`

## Objective

Add a non-executing promotion gate for a generated next bounded smoke
iteration run review packet. The gate may approve only bounded-run promotion
into a later separate cycle-contract-generation branch. It does not approve
production scanning, grant production promotion, generate a cycle contract, or
execute anything.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_run_promotion_gate.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_run_promotion_gate.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_run_promotion_gate_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_run_promotion_gate(...)`, the
launcher
`run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_launcher(...)`,
the CLI command
`launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate`, and task
graph support for capability
`launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate`.

Required builder inputs are `run_review_packet_output_dir`, `output_dir`, and
`promotion_gate_id`. Optional metadata is `project_id`, `reviewer_id`, and
`operator_notes`. No human approval phrase or plaintext approval phrase is
accepted by this gate.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate \
  --run-review-packet-output-dir /path/to/run-review-packet-output \
  --output-dir /path/to/run-promotion-gate-output \
  --promotion-gate-id run-promotion-gate-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

## Schema

The promotion gate JSON uses `gate_type:
local_asset_next_bounded_smoke_iteration_run_promotion_gate_v1`, `authority:
non_authority_bounded_run_promotion_gate_record`, and
`execution_capability:
local_asset_next_bounded_smoke_iteration_run_promotion_gate_only`.

It records gate metadata, inherited review packet/runner/request/run facts,
source review fields, gate status, gate decision, next allowed action,
bounded-run promotion approval, cycle-contract-generation allowance,
`cycle_contract_generated=false`, production scan and production promotion
denials, source artifact refs, missing/untrusted artifacts, gate blockers,
disallowed actions, deterministic ordering, human approval/review
requirements, and explicit false boundary flags.

The manifest uses `manifest_type:
local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_v1` and
binds the gate, summary, checklist, source artifact refs, hashes, gate status,
gate decision, next allowed action, bounded-run approval, cycle-contract
allowance, production denials, and explicit false gate boundary flags.

## Source Artifact Policy

The gate reads only generated run review packet artifacts by explicit filename
from `run_review_packet_output_dir`. It does not recursively index that
directory, runner output, actual next iteration output, upstream cycle output,
or candidate input files.

Required source artifacts:

- `local_asset_next_bounded_smoke_iteration_run_review_packet.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional source artifacts:

- `local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md`

Malformed JSON, source artifact symlinks, missing required type fields, type
mismatches, and hash mismatches are untrusted. The review packet manifest must
hash-bind the review packet and optional summary/checklist when present. The
artifact index manifest must hash-bind the source artifact index.

## Required Artifacts

The gate output directory must already exist. It receives:

- `local_asset_next_bounded_smoke_iteration_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed on existing files or symlink
collisions at expected output paths.

## Promotion Gate Readiness Rules

The gate is ready only when the source review packet reports:

- `review_status =
  next_bounded_smoke_iteration_run_review_packet_ready`
- `review_decision =
  package_next_bounded_smoke_iteration_run_for_promotion_gate_review`
- `next_allowed_action =
  run_next_bounded_smoke_iteration_run_promotion_gate`
- `review_packet_created=true`
- source promotion, production scan, production promotion, automatic approval,
  autonomy, runner re-execution, candidate access, mutation, media organizer,
  output overwrite, network, model, external runtime, and production scan
  recommendation flags are explicitly boolean false
- `required_human_approval=true`
- `required_human_review=true`
- all cross-artifact checks passed
- review blockers, missing required artifacts, and untrusted artifacts are empty
- deterministic ordering is true

Inherited reviewed run facts must also be safe: runner execution and next
bounded smoke iteration execution are true; candidate limits were enforced;
candidate symlink metadata is empty; candidate file count, total bytes, and
max depth are non-negative integers; and bounded file records are sorted by
`relative_path` and contain no raw content fields.

## Bounded-Run-Promotion-Only Rule

When ready, the gate sets `bounded_run_promotion_approved=true`,
`cycle_contract_generation_allowed=true`, and `cycle_contract_generated=false`.
This approves only bounded-run promotion into the later cycle-contract stage.
It does not approve production scan, grant production promotion, or generate a
cycle contract.

## Source Boundary Boolean Fail-Closed Policy

Missing or non-boolean required source safety fields block with
`blocked_invalid_review_packet_record`. Required source boundary booleans set
to unsafe values block with `blocked_source_boundary_violation`. This applies
before bounded-run promotion can be approved.

## Blocker Logic

Missing required generated artifacts produce
`blocked_missing_required_artifacts`. Untrusted generated artifacts produce
`blocked_untrusted_artifacts`. A non-ready review packet produces
`blocked_review_packet_not_ready`. Malformed source review packet fields
produce `blocked_invalid_review_packet_record`. Source boundary violations
produce `blocked_source_boundary_violation`. Invalid inherited run facts
produce `blocked_invalid_reviewed_run_facts`. Failed cross-artifact checks or
source review blockers produce `blocked_review_packet_contains_blockers`.
Invalid gate metadata produces `blocked_invalid_promotion_gate_metadata`.

## Generated-Artifacts-Only Policy

The gate never scans, stats, lists, reads, or hashes live candidate inputs.
Candidate metadata is consumed only as inert strings and metadata already
present in the generated review packet.

## No Live Candidate Access Policy

The gate, manifest, launcher payload, and task graph node record report
`candidate_input_path_checked_by_gate=false`,
`candidate_input_path_listed_by_gate=false`,
`candidate_input_file_read_by_gate=false`, and
`candidate_input_file_hashing_performed_by_gate=false`.

## Artifact Index Relationship

The local output `artifact_index.json` binds only the promotion gate,
promotion gate manifest, summary, and checklist. The index manifest binds that
artifact index. It does not recursively index source directories or candidate
inputs.

## Task Graph Relationship

The local asset adapter registry admits
`launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate`. Task
graph execution records the promotion gate artifact paths, gate status, gate
decision, next allowed action, inherited metadata, bounded-run promotion
approval, cycle-contract-generation allowance, `cycle_contract_generated=false`,
human approval/review requirements, and explicit false boundary flags. Task
graph artifact output binding adds the four promotion gate roles.

## Failure Behavior

If `output_dir` is missing, unsafe, overlapping with the source directory, or
already contains expected promotion gate output files, the builder returns a
structured failure and writes no artifacts. If the source review packet
directory is missing or unsafe while `output_dir` is safe, it writes a blocked
promotion gate artifact without creating or mutating source directories.

## Deterministic Ordering

Source artifacts are sorted by role. Bounded file records must already be
sorted by `relative_path`. Checklist items, disallowed actions, source
artifact roles, and artifact index entries are emitted in stable order.

## Explicit Non-Behavior

This branch does not run readiness, human smoke, smoke review packet
generation, smoke promotion gate generation, bounded smoke iteration,
iteration review packet generation, iteration promotion gate generation, cycle
contract generation, cycle human review generation, next admission generation,
execution request generation, runner admission generation, runner execution,
or run review packet generation. It does not scan candidate inputs, validate
live candidate paths, list candidate directories, read candidate file
contents, hash candidate files, create actual iteration output directories,
create runner output directories, move/rename/delete files, deduplicate files,
copy raw private content, add media organizer behavior, upload anything, use
network access, call model APIs, invoke external runtimes, add UI, add
Operator Console behavior, add watcher/daemon behavior, add global database
state, grant automatic approval, grant autonomous execution, approve
production scan, or grant production promotion.

## Validation Commands

Required validation for this branch includes:

```bash
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_run_promotion_gate -v
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_run_review_packet -v
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner -v
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner_admission -v
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_execution_request -v
python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_admission -v
python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_human_review -v
python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_contract -v
python3 -m unittest tests.tracer_bullet.test_local_asset_iteration_promotion_gate -v
python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_iteration_review_packet -v
python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_iteration -v
python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v
python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v
python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v
python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v
python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v
python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v
python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v
python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v
python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v
python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v
python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v
python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v
python3 -m unittest discover -s tests/schemas -v
python3 -m unittest discover -s validation/tests/acceptance -v
python3 -m unittest discover -s tests/tracer_bullet -v
python3 -m unittest tests.personal_ai.test_product_health_check -v
python3 -m unittest tests.personal_ai.test_adapter_registry -v
make ci
git diff --check
git status --short
```

## Final Verification State

Final post-continuation `make ci` result: see PR #415 continuation report.

Final `git diff --check` result: see PR #415 continuation report.

Final `git status --short` result: see PR #415 continuation report.

Final branch verification state: PR #415 continuation validation report is the
source of truth. No new branch or PR is required for this gate.

## Next Recommended Branch

Add the later separate cycle-contract-generation branch that consumes only a
ready next bounded smoke iteration run promotion gate and still keeps
production scanning and production promotion separate.
