# Local Asset Next Bounded Smoke Iteration Execution Request v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`<repo-root>`

Branch:
`feat/local-asset-next-bounded-smoke-iteration-execution-request-v1`

## Objective

Add a non-executing future execution request layer after next bounded smoke
iteration admission. The layer consumes generated next admission artifacts and
emits a durable request artifact describing the intended future bounded smoke
iteration, requested limits, and optional operator metadata.

The layer creates an execution request record only. It does not execute the
next bounded smoke iteration, create the future iteration output directory,
scan, validate candidate paths, read candidate content, hash candidate input
files, mutate upstream outputs, or grant production authority.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_execution_request.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_execution_request.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_execution_request_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_execution_request(...)` and the
CLI command
`launch-local-asset-next-bounded-smoke-iteration-execution-request`.

Required inputs:

- `next_admission_output_dir`
- `output_dir`
- `requested_next_iteration_id`
- `requested_candidate_input_dir`
- `requested_next_iteration_output_dir`
- `requested_max_files`
- `requested_max_total_bytes`
- `requested_max_depth`

Optional metadata:

- `project_id`
- `request_id`
- `operator_id`
- `operator_notes`
- `requested_compare_previous_scan_manifest_path`
- `requested_previous_iteration_artifact_index_path`

The builder writes only to an existing, separate output directory. All writes
are exclusive. Missing output directories, existing output files, symlinked
output roots, and unsafe input/output overlap fail closed without writing
request artifacts. If the next admission output directory is missing or unsafe
but the request output directory is safe, the builder writes a blocked request
artifact without creating or mutating the next admission root.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-execution-request \
  --next-admission-output-dir /path/to/next-admission-output \
  --output-dir /path/to/execution-request-output \
  --requested-next-iteration-id iteration-002 \
  --requested-candidate-input-dir /path/to/future-candidate-input \
  --requested-next-iteration-output-dir /path/to/future-iteration-output \
  --requested-max-files 25 \
  --requested-max-total-bytes 104857600 \
  --requested-max-depth 4 \
  --project-id demo_project \
  --request-id request-002 \
  --operator-id operator-001 \
  --operator-notes "optional notes"
```

## Schema

The request JSON uses `request_type:
local_asset_next_bounded_smoke_iteration_execution_request_v1`, `authority:
non_authority_execution_request_record`, and `execution_capability:
local_asset_next_bounded_smoke_iteration_execution_request_only`.

It records project and request metadata, requested future iteration metadata,
requested limits, source admission fields, request status, request decision,
next allowed action, future request creation, execute denial, next-iteration
execution/output denial, requested output creation denial, candidate access
denial, production denial, automatic approval denial, autonomy denial, source
artifact trust state, missing/untrusted artifact lists, blocker lists,
deterministic ordering, human approval/review requirements, disallowed
actions, and explicit false boundary flags.

Request status values:

- `next_bounded_smoke_iteration_execution_request_ready`
- `blocked_missing_required_artifacts`
- `blocked_untrusted_artifacts`
- `blocked_admission_not_ready`
- `blocked_prepare_not_admitted`
- `blocked_execution_already_allowed`
- `blocked_iteration_already_executed`
- `blocked_next_iteration_output_already_created`
- `blocked_production_boundary_violation`
- `blocked_invalid_requested_limits`
- `blocked_invalid_requested_metadata`
- `blocked_invalid_admission_record`
- `blocked_unknown`

Request decision values:

- `create_future_bounded_smoke_iteration_execution_request`
- `reject_and_repair_artifacts`
- `reject_and_repair_admission`
- `reject_and_repair_request`
- `reject_boundary_violation`

Next allowed action values:

- `await_separate_bounded_smoke_iteration_runner`
- `repair_artifacts`
- `repair_admission`
- `repair_request`
- `reject_boundary_violation`

## Source Artifact Policy

The request builder reads and hashes only generated artifacts in the declared
next admission output directory. It does not recursively index the next
admission output directory, cycle human review output directory, cycle
contract output directory, upstream output directories, or candidate input
files. It does not read raw private content, hash candidate input files, copy
raw private content, inspect candidate payloads, or validate candidate paths.

No human signoff phrase is accepted by this branch. No plaintext approval
phrase is handled by this branch.

## Required Artifacts

Required generated next admission artifacts:

- `local_asset_next_bounded_smoke_iteration_admission.json`
- `local_asset_next_bounded_smoke_iteration_admission_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated next admission artifacts are bound when present:

- `local_asset_next_bounded_smoke_iteration_admission_summary.md`
- `local_asset_next_bounded_smoke_iteration_admission_checklist.md`

Trust checks verify expected generated artifact type fields, the admission
manifest admission hash, optional summary/checklist hashes when those files
are present, and the artifact index manifest hash for the admission artifact
index. Malformed JSON marks the source artifact untrusted.

## Request Readiness Rules

The request is ready only when all required generated next admission artifacts
exist and are trusted; manifest hashes match; admission status is
`next_bounded_smoke_iteration_admission_ready`; admission decision is
`admit_prepare_next_bounded_smoke_iteration`; admission next allowed action is
`create_next_bounded_smoke_iteration_execution_request`; prepare is admitted;
source execute permission is false; source next iteration execution is false;
source next iteration output creation is false; production scan, production
promotion, automatic approval, and autonomous execution are false; requested
metadata is non-empty; requested limits are valid; and no missing, untrusted,
production, mutation, execution, candidate validation/listing/read/hash, or
metadata blockers exist.

When ready, the record emits:

- `request_status: next_bounded_smoke_iteration_execution_request_ready`
- `request_decision: create_future_bounded_smoke_iteration_execution_request`
- `next_allowed_action: await_separate_bounded_smoke_iteration_runner`
- `future_execution_request_created: true`
- `next_bounded_smoke_iteration_execute_allowed: false`
- `next_bounded_smoke_iteration_executed: false`
- `next_iteration_output_dir_created: false`
- `requested_next_iteration_output_dir_created: false`

## Blocker Logic

Missing required artifacts map to `blocked_missing_required_artifacts`,
`reject_and_repair_artifacts`, and `repair_artifacts`.

Untrusted artifacts map to `blocked_untrusted_artifacts`,
`reject_and_repair_artifacts`, and `repair_artifacts`.

Malformed or internally inconsistent next admission records map to
`blocked_invalid_admission_record`, `reject_and_repair_admission`, and
`repair_admission`.

Not-ready admission status maps to `blocked_admission_not_ready`,
`reject_and_repair_admission`, and `repair_admission`.

Prepare denial maps to `blocked_prepare_not_admitted`,
`reject_and_repair_admission`, and `repair_admission`.

Existing execute permission maps to `blocked_execution_already_allowed`,
`reject_boundary_violation`, and `reject_boundary_violation`.

Existing next iteration execution maps to `blocked_iteration_already_executed`,
`reject_boundary_violation`, and `reject_boundary_violation`.

Existing next iteration output creation maps to
`blocked_next_iteration_output_already_created`, `reject_boundary_violation`,
and `reject_boundary_violation`.

Production, mutation, candidate access, automatic approval, autonomy, or
similar boundary violations map to `blocked_production_boundary_violation`,
`reject_boundary_violation`, and `reject_boundary_violation`.

Invalid requested limits map to `blocked_invalid_requested_limits`,
`reject_and_repair_request`, and `repair_request`.

Invalid requested metadata maps to `blocked_invalid_requested_metadata`,
`reject_and_repair_request`, and `repair_request`.

## Requested Metadata Policy

Requested candidate input directory, requested next iteration output
directory, optional previous scan manifest path, and optional previous
iteration artifact index path are stored as path metadata only. They are not
created, statted, resolved strictly, listed, read, hashed, copied, validated,
or mutated. Empty requested next iteration id, requested candidate input
directory, or requested next iteration output directory fails closed. Requested
limits must be integers with `requested_max_files >= 1`,
`requested_max_total_bytes >= 1`, and `requested_max_depth >= 0`.

## Artifact Index Relationship

The request `artifact_index.json` binds only the four request artifacts:

- `local_asset_next_bounded_smoke_iteration_execution_request`
- `local_asset_next_bounded_smoke_iteration_execution_request_manifest`
- `local_asset_next_bounded_smoke_iteration_execution_request_summary`
- `local_asset_next_bounded_smoke_iteration_execution_request_checklist`

It does not recursively index the next admission output directory, cycle human
review output directory, cycle contract output directory, upstream output
roots, or candidate input files.

The request manifest records hashes for the request JSON, summary, checklist,
and named source generated next admission artifacts.

## Task Graph Relationship

The local asset task graph supports `adapter_id: local_asset_runtime` with
`capability:
launch_local_asset_next_bounded_smoke_iteration_execution_request`. The node
exposes request paths, request status, request decision, next allowed action,
requested metadata and limits, future request creation, execute denial,
next-iteration execution/output denial, requested output creation denial,
candidate access denial, human approval/review requirements, and explicit
false boundary flags.

`task_graph_artifact_outputs.py` binds the four request artifact roles:

- `local_asset_next_bounded_smoke_iteration_execution_request`
- `local_asset_next_bounded_smoke_iteration_execution_request_manifest`
- `local_asset_next_bounded_smoke_iteration_execution_request_summary`
- `local_asset_next_bounded_smoke_iteration_execution_request_checklist`

## Failure Behavior

Unsafe or missing request output directories and expected output collisions
return structured failure payloads and write no artifacts. Missing or unsafe
next admission directories write blocked request artifacts only when the
request output directory is safe. Missing required source artifacts, untrusted
source artifacts, malformed admission records, request metadata errors, and
boundary violations produce durable blocked request artifacts for review and
repair.

## Deterministic Ordering

Source artifact records, blocker lists, checklist items, artifact index
entries, and manifest role maps are emitted in deterministic order. The
request record, manifest, artifact index, and task graph node all set
`deterministic_ordering: true` where applicable.

## Explicit Non-Behavior

This branch does not run scan, readiness, human smoke, smoke review packet
generation, smoke promotion gate, bounded smoke iteration, iteration review
packet generation, iteration promotion gate, cycle contract generation, cycle
human review generation, or next admission generation. It does not execute the
next bounded smoke iteration, create a next iteration output directory, create
the requested next iteration output directory, validate candidate paths, list
candidate directories, read raw candidate file contents, hash candidate input
files, mutate upstream outputs, mutate candidate input, move, rename, delete,
or deduplicate files, add media organizer behavior, approve production scan,
grant production promotion, add automatic approval, add autonomous execution,
add watcher/daemon behavior, add UI, add Operator Console behavior, add global
database state, use network access, call model APIs, invoke external creative
runtimes, or modify HFX.

## Validation Commands

All requested validation commands were run. The focused and discovery suites
passed before commit; `make ci` was then rerun after commit and passed in a
clean worktree.

- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_execution_request -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_admission -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_human_review -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_contract -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_iteration_promotion_gate -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_iteration_review_packet -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_iteration -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v` -> pass
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v` -> pass
- `python3 -m unittest discover -s tests/schemas -v` -> pass, 133 tests
- `python3 -m unittest discover -s validation/tests/acceptance -v` -> pass, 156 tests
- `python3 -m unittest discover -s tests/tracer_bullet -v` -> pass, 6,586 tests, 4 skipped
- `python3 -m unittest tests.personal_ai.test_product_health_check -v` -> pass
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v` -> pass
- `make ci` -> pass after commit
- `git diff --check` -> pass
- `git status --short` -> clean

## Final Validation State

- Final post-commit `make ci` result: pass
- Final `git diff --check` result: pass
- Final `git status --short` result: clean
- Final branch verification state: branch
  `feat/local-asset-next-bounded-smoke-iteration-execution-request-v1`
  pushed, draft PR #411 opened against main, post-commit validation passed,
  final `git diff --check` passed, and final `git status --short` was clean.

## Next Recommended Branch

`feat/local-asset-next-bounded-smoke-iteration-runner-admission-v1`
