# Local Asset Next Bounded Smoke Iteration Runner Admission v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch:
`feat/local-asset-next-bounded-smoke-iteration-runner-admission-v1`

## Objective

Add a non-executing runner admission layer after the next bounded smoke
iteration execution request. The layer consumes generated execution request
artifacts and emits a durable runner admission artifact stating whether a
later, separate bounded smoke iteration runner may consume the request.

The layer is runner-admission-only. It does not execute the runner, execute the
next bounded smoke iteration, create the future output directory, inspect
candidate paths, read candidate content, hash candidate input files, mutate
upstream outputs, or grant production authority.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_runner_admission.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_runner_admission.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_runner_admission_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_runner_admission(...)` and the
CLI command
`launch-local-asset-next-bounded-smoke-iteration-runner-admission`.

Required inputs:

- `execution_request_output_dir`
- `output_dir`
- `runner_admission_id`
- `runner_operator_id`
- `runner_operator_acknowledgement_phrase`
- `admitted_runner_id`
- `admitted_runner_version`
- `admitted_max_files`
- `admitted_max_total_bytes`
- `admitted_max_depth`

Optional metadata:

- `project_id`
- `operator_notes`
- `runner_environment_label`

The builder writes only to an existing, separate output directory. All writes
are exclusive. Missing output directories, existing output files, symlinked
output roots, and unsafe input/output overlap fail closed without writing
runner admission artifacts. If the execution request output directory is
missing or unsafe but the runner admission output directory is safe, the
builder writes a blocked runner admission artifact without creating or
mutating the execution request root.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-runner-admission \
  --execution-request-output-dir /path/to/execution-request-output \
  --output-dir /path/to/runner-admission-output \
  --runner-admission-id runner-admission-002 \
  --runner-operator-id operator-001 \
  --runner-operator-acknowledgement-phrase I_ACKNOWLEDGE_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ONLY \
  --admitted-runner-id bounded-smoke-runner \
  --admitted-runner-version 1.0.0 \
  --admitted-max-files 25 \
  --admitted-max-total-bytes 104857600 \
  --admitted-max-depth 4 \
  --project-id demo_project \
  --operator-notes "optional notes" \
  --runner-environment-label local-fixture
```

## Schema

The runner admission JSON uses `admission_type:
local_asset_next_bounded_smoke_iteration_runner_admission_v1`, `authority:
non_authority_runner_admission_record`, and `execution_capability:
local_asset_next_bounded_smoke_iteration_runner_admission_only`.

It records project metadata, runner admission identity, runner operator
identity, the runner acknowledgement SHA-256 hash, admitted runner
identity/version, optional runner environment label and notes, source request
metadata, requested limits, admitted limits, source request readiness fields,
runner admission status, runner admission decision, next allowed action,
runner consume admission, runner execution denial, next-iteration
execution/output denial, requested future output creation denial, candidate
access denial, production denial, automatic approval denial, autonomy denial,
source artifact trust state, missing/untrusted artifact lists, blocker lists,
deterministic ordering, human approval/review requirements, disallowed actions,
and explicit false boundary flags.

Runner admission status values:

- `next_bounded_smoke_iteration_runner_admission_ready`
- `blocked_missing_required_artifacts`
- `blocked_untrusted_artifacts`
- `blocked_invalid_runner_acknowledgement`
- `blocked_invalid_runner_metadata`
- `blocked_invalid_admitted_limits`
- `blocked_limits_exceed_request`
- `blocked_execution_request_not_ready`
- `blocked_future_request_not_created`
- `blocked_execution_already_allowed`
- `blocked_iteration_already_executed`
- `blocked_next_iteration_output_already_created`
- `blocked_candidate_path_access_violation`
- `blocked_production_boundary_violation`
- `blocked_invalid_execution_request_record`
- `blocked_unknown`

Runner admission decision values:

- `admit_runner_to_consume_future_execution_request`
- `reject_and_repair_artifacts`
- `reject_and_repair_runner_admission`
- `reject_and_repair_execution_request`
- `reject_boundary_violation`

Next allowed action values:

- `await_separate_bounded_smoke_iteration_runner_execution`
- `repair_artifacts`
- `repair_runner_admission`
- `repair_execution_request`
- `reject_boundary_violation`

## Source Artifact Policy

The runner admission builder reads and hashes only generated artifacts in the
declared execution request output directory:

- `local_asset_next_bounded_smoke_iteration_execution_request.json`
- `local_asset_next_bounded_smoke_iteration_execution_request_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional execution request summary and checklist markdown files when present

It verifies generated artifact type fields and manifest hashes. Malformed JSON
is marked untrusted. The builder does not recursively index the execution
request output directory, next admission output directory, cycle human review
output directory, cycle contract output directory, upstream output
directories, or candidate input files.

## Required Artifacts

The runner admission output directory receives:

- `local_asset_next_bounded_smoke_iteration_runner_admission.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_summary.md`
- `local_asset_next_bounded_smoke_iteration_runner_admission_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

## Runner Admission Readiness Rules

Runner admission is ready only when the execution request artifact exists and
is trusted; the execution request manifest exists and hashes match; the
execution request artifact index exists; the artifact index manifest exists
and hashes match; request status is
`next_bounded_smoke_iteration_execution_request_ready`; request decision is
`create_future_bounded_smoke_iteration_execution_request`; request next action
is `await_separate_bounded_smoke_iteration_runner`; the future execution
request was created; source execute permission, next iteration execution,
future output creation, requested future output creation, candidate path
checking/listing/read/hash flags, production approval, production promotion,
automatic approval, and autonomous execution are false; the runner
acknowledgement phrase exactly matches the required phrase; plaintext
acknowledgement is not persisted; runner metadata is non-empty; admitted limits
are valid; admitted limits do not exceed requested limits; there are no missing
or untrusted artifacts; and all boundary flags remain false.

Ready output records
`admission_status: next_bounded_smoke_iteration_runner_admission_ready`,
`admission_decision: admit_runner_to_consume_future_execution_request`,
`next_allowed_action: await_separate_bounded_smoke_iteration_runner_execution`,
and `runner_consume_request_admitted: true`. It still records
`runner_execution_allowed: false` and
`next_bounded_smoke_iteration_execute_allowed: false`.

## Blocker Logic

Missing required artifacts and untrusted artifacts repair artifacts. Invalid
runner acknowledgement, invalid runner metadata, invalid admitted limits, and
admitted limits that exceed requested limits repair runner admission. Malformed
execution request records, non-ready execution requests, and missing future
request creation repair the execution request. Existing execute permission,
already-executed iterations, already-created future output directories,
candidate path access, production approval, mutation, automatic approval, and
autonomous execution reject the boundary.

## Runner Acknowledgement Hash-Only Policy

The required acknowledgement phrase is
`I_ACKNOWLEDGE_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ONLY`.

The builder validates the plaintext phrase in memory and stores only its
SHA-256 hash in output artifacts. It never persists the plaintext phrase.
Invalid acknowledgement produces a blocked runner admission artifact when
`output_dir` is safe.

## Admitted Limit Policy

`admitted_max_files` and `admitted_max_total_bytes` must be positive integers.
`admitted_max_depth` must be an integer greater than or equal to zero. Admitted
limits must be less than or equal to the requested limits inherited from the
trusted execution request artifact.

## Inherited Requested Metadata Policy

Requested candidate input path, requested next iteration output path, previous
scan manifest path, and previous iteration artifact index path are copied only
as inherited metadata from the trusted execution request artifact. The runner
admission builder does not create, strict-resolve, stat, list, validate, read,
hash, or mutate those paths.

## Artifact Index Relationship

`artifact_index.json` binds only the runner admission JSON, manifest, summary,
and checklist. It does not recursively index upstream output directories or
candidate inputs. `artifact_index_manifest.json` binds the runner admission
artifact index hash and role map.

## Task Graph Relationship

The `local_asset_runtime` adapter now enumerates
`launch_local_asset_next_bounded_smoke_iteration_runner_admission`. Task graph
nodes for that capability call the launcher, expose runner admission artifact
paths, admission status/decision/action, requested and admitted limits, runner
consume admission, runner execution denial, next-iteration execution/output
denial, candidate access denial, human approval/review requirements, and false
boundary flags. Task graph artifact output binding records the four runner
admission artifact roles plus the local artifact index paths.

## Failure Behavior

Unsafe or missing `output_dir`, existing output files, and unsafe input/output
overlap return structured failure with no artifacts written. Missing or unsafe
execution request roots write blocked runner admission artifacts only when
`output_dir` is safe. The builder does not create the execution request root
and does not mutate upstream output directories.

## Deterministic Ordering

Source artifact records, missing artifact lists, untrusted artifact lists,
blockers, checklist items, and artifact index roles are emitted in stable,
deterministic order.

## Explicit Non-Behavior

This branch does not run scan, readiness, human smoke, smoke review packet,
smoke promotion gate, bounded smoke iteration, iteration review packet,
iteration promotion gate, cycle contract generation, cycle human review
generation, next admission generation, or execution request generation. It
does not execute the next bounded smoke iteration, execute the runner, create a
next iteration output directory, validate candidate paths, stat candidate
paths, list candidate directories, read raw candidate file contents, hash
candidate input files, mutate upstream outputs, mutate candidate input, move,
rename, delete, or deduplicate files, add media organizer behavior, approve
production scanning, grant production promotion, add UI, add Operator Console,
add watcher/daemon behavior, use network access, call model APIs, invoke
external runtimes, modify HFX, or grant autonomy.

## Validation Commands

All requested validation commands were run. The focused and discovery suites
passed. A pre-commit `make ci` invocation ran the test/discovery portions and
then stopped at the clean-worktree guard because the branch still had
uncommitted edits. After committing, `make ci` was rerun from a clean worktree
and passed.

- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner_admission -v` -> pass, 23 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_execution_request -v` -> pass, 20 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_admission -v` -> pass, 15 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_human_review -v` -> pass, 22 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_contract -v` -> pass, 15 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_iteration_promotion_gate -v` -> pass, 13 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_iteration_review_packet -v` -> pass, 13 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_iteration -v` -> pass, 12 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v` -> pass, 12 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v` -> pass, 11 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v` -> pass, 12 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v` -> pass, 10 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v` -> pass, 12 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v` -> pass, 10 tests
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v` -> pass, 8 tests
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v` -> pass, 7 tests
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v` -> pass, 10 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v` -> pass, 5 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v` -> pass, 4 tests
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v` -> pass, 12 tests
- `python3 -m unittest discover -s tests/schemas -v` -> pass, 133 tests
- `python3 -m unittest discover -s validation/tests/acceptance -v` -> pass, 156 tests
- `python3 -m unittest discover -s tests/tracer_bullet -v` -> pass, 6,609 tests, 4 skipped
- `python3 -m unittest tests.personal_ai.test_product_health_check -v` -> pass, 5 tests
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v` -> pass, 8 tests
- `make ci` -> pass after commit
- `git diff --check` -> pass
- `git status --short` -> clean

## Final Validation State

- Final post-commit `make ci` result: pass
- Final `git diff --check` result: pass
- Final `git status --short` result: clean
- Final branch verification state: branch
  `feat/local-asset-next-bounded-smoke-iteration-runner-admission-v1`
  pushed to origin, draft PR #412 opened against main, post-commit `make ci`
  passed, final `git diff --check` passed, and final `git status --short`
  was clean.

## Next Recommended Branch

`feat/local-asset-next-bounded-smoke-iteration-runner-v1`
