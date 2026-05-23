# Local Asset Next Bounded Smoke Iteration Runner v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch:
`feat/local-asset-next-bounded-smoke-iteration-runner-v1`

## Objective

Add the actual bounded local runner for the next bounded smoke iteration. The
runner consumes trusted generated runner admission artifacts, validates a
separate execution acknowledgement, checks the requested actual output
directory, then validates and traverses the requested candidate input directory
only under admitted limits.

The result is routed to human review. The branch does not grant production
scan, production promotion, automatic approval, or autonomous execution.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_runner.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_runner.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_runner_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_runner(...)` and the CLI
command `launch-local-asset-next-bounded-smoke-iteration-runner`.

Required inputs:

- `runner_admission_output_dir`
- `runner_output_dir`
- `actual_next_iteration_output_dir`
- `runner_execution_id`
- `runner_operator_id`
- `runner_execution_acknowledgement_phrase`

Optional metadata:

- `project_id`
- `operator_notes`

The runner output directory and actual next iteration output directory must
already exist. The runner does not create the candidate input directory or the
actual next iteration output directory. Output writes are exclusive and fail
closed on existing files.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-runner \
  --runner-admission-output-dir /path/to/runner-admission-output \
  --runner-output-dir /path/to/runner-output \
  --actual-next-iteration-output-dir /path/to/future-iteration-output \
  --runner-execution-id runner-execution-002 \
  --runner-operator-id operator-001 \
  --runner-execution-acknowledgement-phrase I_EXECUTE_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_UNDER_ADMITTED_LIMITS \
  --project-id demo_project \
  --operator-notes "optional notes"
```

## Schema

The runner JSON uses `runner_type:
local_asset_next_bounded_smoke_iteration_runner_v1`, `authority:
bounded_smoke_runner_record`, and `execution_capability:
local_asset_next_bounded_smoke_iteration_runner_only`.

It records runner execution identity, runner operator identity, the
acknowledgement phrase SHA-256 hash, source runner admission metadata,
requested/admitted limits, source readiness fields, runner status, runner
decision, next allowed action, execution flags, candidate bounded metadata,
bounded file records, actual iteration artifact refs, source artifact refs,
missing/untrusted artifacts, blockers, deterministic ordering, human
approval/review requirements, disallowed actions, and explicit production,
autonomy, mutation, media organizer, network, model, and external runtime
boundary flags.

The actual iteration output schema includes
`local_asset_next_bounded_smoke_iteration_run.json`,
`local_asset_next_bounded_smoke_iteration_run_manifest.json`, and
`local_asset_next_bounded_smoke_iteration_candidate_manifest.json`. The
candidate manifest uses `manifest_type:
local_asset_next_bounded_smoke_iteration_candidate_manifest_v1`.

## Source Artifact Policy

The runner reads only generated artifacts in the runner admission output
directory:

- `local_asset_next_bounded_smoke_iteration_runner_admission.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional runner admission summary and checklist markdown files when present

It verifies generated type fields and manifest hashes. Malformed JSON is
untrusted. It does not recursively index the runner admission output
directory, execution request output directory, next admission output
directory, cycle human review output directory, cycle contract output
directory, upstream output directories, actual next iteration output
directory, or candidate input directory.

## Required Artifacts

The runner output directory receives:

- `local_asset_next_bounded_smoke_iteration_runner.json`
- `local_asset_next_bounded_smoke_iteration_runner_manifest.json`
- `local_asset_next_bounded_smoke_iteration_runner_summary.md`
- `local_asset_next_bounded_smoke_iteration_runner_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

On successful execution, the actual next iteration output directory receives:

- `local_asset_next_bounded_smoke_iteration_run.json`
- `local_asset_next_bounded_smoke_iteration_run_manifest.json`
- `local_asset_next_bounded_smoke_iteration_candidate_manifest.json`
- `local_asset_next_bounded_smoke_iteration_summary.md`
- `local_asset_next_bounded_smoke_iteration_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

## Runner Execution Readiness Rules

Runner execution is allowed only when the runner admission artifact exists and
is trusted; the runner admission manifest exists and hashes match; the runner
admission artifact index exists; the artifact index manifest exists and hashes
match; runner admission status is
`next_bounded_smoke_iteration_runner_admission_ready`; runner admission
decision is `admit_runner_to_consume_future_execution_request`; next allowed
action is `await_separate_bounded_smoke_iteration_runner_execution`;
`runner_consume_request_admitted` is true; source execution, next iteration
execution, next output creation, requested output creation, candidate access,
production approval, production promotion, automatic approval, and autonomy
flags are false; runner execution metadata is non-empty; the acknowledgement
phrase is valid; admitted limits are present and valid; requested candidate
input and next iteration output paths are present; the actual output directory
textually matches the requested output directory; and there are no output
collisions or unsafe path overlaps.

## Blocker Logic

Missing source artifacts and untrusted source artifacts repair artifacts.
Invalid execution acknowledgement and invalid runner metadata repair the
runner. Invalid or non-ready runner admission repairs runner admission.
Existing execution permission, already executed iteration, output creation,
candidate access precondition violations, production boundary violations, and
unsafe overlaps reject the boundary. Unsafe actual output directories,
candidate directories, candidate symlinks, and admitted-limit excesses write
blocked runner receipts without writing actual iteration artifacts.

## Acknowledgement Hash-Only Policy

The required execution acknowledgement phrase is
`I_EXECUTE_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_UNDER_ADMITTED_LIMITS`.

The runner validates the plaintext phrase in memory and stores only its
SHA-256 hash. The plaintext phrase is not persisted in runner JSON, manifest,
summary, checklist, artifact index, or artifact index manifest files.

## Admitted Limit Enforcement

Candidate traversal is bounded by `admitted_max_files`,
`admitted_max_total_bytes`, and `admitted_max_depth`. If any admitted limit
would be exceeded, the runner fails closed before writing actual iteration
artifacts.

## Candidate Metadata And Hash Policy

Candidate records are deterministic and contain relative path, size in bytes,
SHA-256 hash, depth, `is_symlink: false`, `content_copied: false`, and
`raw_content_copied: false`. The runner reads file bytes only to compute
SHA-256 hashes. It does not copy raw content, persist previews, extract text,
or record image/video metadata beyond bounded file metadata.

## Symlink Policy

The requested candidate root and actual output root must not be symlinks.
Candidate traversal uses non-following filesystem operations and fails closed
on symlinked files or directories discovered inside the bounded traversal.

## Artifact Index Relationship

The runner artifact index binds only the four runner receipt artifacts. It
does not recursively index runner admission output, execution request output,
actual next iteration output, upstream output, or candidate input files.

The actual next iteration artifact index binds only the explicit actual
iteration artifacts generated by this runner. Candidate file records are bound
inside the candidate manifest, not the runner artifact index.

## Task Graph Relationship

The local task graph supports `adapter_id: local_asset_runtime` with
`capability: launch_local_asset_next_bounded_smoke_iteration_runner`. The node
records runner artifact paths, actual iteration artifact refs, runner status,
runner decision, next allowed action, execution flags, bounded candidate
totals, human approval/review requirements, and explicit false production,
autonomy, mutation, media organizer, network, model, and external runtime
flags.

## Failure Behavior

Missing or unsafe runner output directories and preexisting runner output
files produce structured failure payloads and write no artifacts. Missing,
unsafe, mismatched, or colliding actual output directories write a blocked
runner receipt when the runner output directory is safe, except hard path
overlap cases that write no artifacts. Missing or unsafe runner admission
artifacts write a blocked runner receipt when the runner output directory is
safe and do not touch candidate or actual iteration paths.

## Deterministic Ordering

Source artifact refs are ordered by explicit role list. Candidate records are
sorted by relative path. Artifact index entries are explicit and stable.

## Explicit Non-Behavior

This branch does not run readiness, human smoke, smoke review packet
generation, smoke promotion gate, previous bounded smoke iteration, iteration
review packet generation, iteration promotion gate, cycle contract
generation, cycle human review generation, next admission generation,
execution request generation, or runner admission generation. It does not
approve production scan, grant production promotion, move, rename, delete, or
deduplicate files, add media organizer behavior, copy raw private content,
upload content, use network access, call model APIs, invoke external creative
runtimes, modify HFX, add UI, add Operator Console, add watcher/daemon
behavior, add global database state, or grant autonomy.

## Validation Commands

- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_runner_admission -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_execution_request -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_admission -v`
- `python3 -m unittest discover -s tests/tracer_bullet -v`
- `python3 -m unittest tests.personal_ai.test_product_health_check -v`
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v`
- `make ci`
- `git diff --check`
- `git status --short`

## Final Verification

- Final post-commit `make ci` result: passed (`6633` tracer/product tests, `156` acceptance tests; `4` skipped)
- Final `git diff --check` result: passed
- Final `git status --short` result: clean
- Final branch verification state: branch `feat/local-asset-next-bounded-smoke-iteration-runner-v1` verified after post-commit validation

## Next Recommended Branch

Prepare a review branch for the next bounded smoke iteration run artifacts
produced by this runner. Do not promote to production scan without a separate
human review and explicit production gate.
