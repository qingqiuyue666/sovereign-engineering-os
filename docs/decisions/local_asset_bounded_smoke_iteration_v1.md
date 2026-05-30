# Local Asset Bounded Smoke Iteration v1

Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`

Canonical local repository path:
`<repo-root>`

Branch name: `feat/local-asset-bounded-smoke-iteration-v1`

## Objective

Add a gated bounded smoke iteration runner for local asset scans. The runner
consumes an existing promotion gate output directory, requires explicit human
signoff, validates that the promotion gate allows only the next bounded smoke
iteration, and delegates the actual bounded scan to the existing
human-approved smoke launcher.

This is not production scanning and is not production promotion.

## Changed Files

- `kernel/assets/local_asset_bounded_smoke_iteration.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_bounded_smoke_iteration.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_bounded_smoke_iteration_v1.md`

## Behavior Added

The new capability adds the chain:

`promotion gate -> explicit human signoff -> next bounded smoke iteration`

The implementation validates the promotion output, candidate input directory,
readiness report, bounded smoke limits, and signoff phrase before invoking the
existing human-approved smoke launcher into `output_dir/smoke/`.

## CLI Command

`launch-local-asset-bounded-smoke-iteration`

Required arguments:

- `--promotion-output-dir`
- `--candidate-input-dir`
- `--readiness-report`
- `--output-dir`
- `--human-signoff-id`
- `--human-signoff-phrase`

Optional arguments:

- `--project-id`
- `--previous-scan-output-dir`
- `--recursive`
- `--include-hidden`
- `--max-smoke-files`
- `--max-smoke-bytes`
- `--max-smoke-depth`

Default limits:

- `max_smoke_files = 100`
- `max_smoke_bytes = 1073741824`
- `max_smoke_depth = 12`

Required signoff phrase:
`I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION`

## Input Validation Rules

- `promotion_output_dir` must exist, be a directory, and not be a symlink.
- `candidate_input_dir` must exist, be a directory, and not be a symlink.
- `readiness_report` must exist, be a file, and not be a symlink.
- `output_dir` must exist, be a directory, and not be a symlink.
- `output_dir` is not created automatically.
- `candidate_input_dir` and `promotion_output_dir` are not created.
- `output_dir` must not equal or overlap `promotion_output_dir` or
  `candidate_input_dir` in either direction.
- `output_dir` must not be inside the review output, smoke output, or previous
  candidate input directory when those paths are discoverable from the
  promotion decision.
- Bounded limits must be non-negative integers.
- Readiness report candidate path, recursive mode, include-hidden mode,
  readiness status, readiness decision, and human approval requirement are
  validated before smoke delegation.

## Promotion Gate Validation Rules

The iteration reads generated promotion artifacts only:

- `local_asset_smoke_promotion_decision.json`
- `local_asset_smoke_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Required promotion conditions:

- `decision_type = local_asset_smoke_promotion_decision_v1`
- `authority = non_authority`
- `execution_capability = local_asset_smoke_promotion_gate_only`
- `promotion_gate_status = promotion_candidate`
- `promotion_decision = allow_next_bounded_smoke_iteration`
- `next_bounded_smoke_iteration_allowed = true`
- `production_promotion_granted = false`
- `production_scan_approved = false`
- `required_human_signoff = true`
- `required_human_approval = true`
- `review_packet_status = review_ready`
- `review_recommended_human_decision = approve_next_bounded_smoke_iteration`
- `promotion_blocker_count = 0`
- `promotion_blockers = []`
- Promotion manifest hashes match the generated decision, summary, and
  checklist when present.
- Promotion artifact index manifest hash matches `artifact_index.json`.

Any failed condition blocks the iteration, writes blocked artifacts only when
the iteration output directory is safe, and does not create or invoke
`smoke/`.

## Human Signoff Artifact

The runner writes
`control/local_asset_bounded_smoke_iteration_signoff.json` with:

- `signoff_type = local_asset_bounded_smoke_iteration_signoff_v1`
- `human_signoff_id`
- `human_signoff_phrase_sha256`
- `human_signoff_phrase_plaintext_persisted = false`
- `human_signoff_phrase_stored = false`
- `required_phrase = I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION`
- `signoff_valid`
- input and output paths
- `required_human_approval = true`
- `next_allowed_action = bounded_smoke_iteration_admission_review`

The submitted signoff phrase is not stored as an input field.

## Admission Artifact

The runner writes
`control/local_asset_bounded_smoke_iteration_admission.json` with admission
state, blockers, promotion hashes, signoff validity, bounded limits, delegated
smoke output path, previous scan output path, and explicit false values for
production promotion, production scan approval, production scan execution,
automatic approval, watcher/daemon behavior, input mutation, file
move/rename/delete, duplicate deletion, media organizer behavior, network
access, model API calls, and external runtime invocation.

## Smoke Launcher Delegation

On valid promotion gate review and valid outer signoff, the runner creates
`output_dir/smoke/` and invokes `run_local_asset_human_smoke_launcher` with:

- `candidate_input_dir`
- `output_dir/smoke`
- `readiness_report`
- `human_approval_id = human_signoff_id`
- `human_approval_phrase = I_APPROVE_LOCAL_ASSET_SMOKE_RUN`
- bounded limits, recursive mode, include-hidden mode, project id, and
  previous scan output directory

The iteration module does not call the local asset scan runtime directly.

## Output Layout

`output_dir/`

- `control/local_asset_bounded_smoke_iteration_signoff.json`
- `control/local_asset_bounded_smoke_iteration_admission.json`
- `smoke/` delegated human-approved smoke outputs when admitted
- `local_asset_bounded_smoke_iteration_result.json`
- `local_asset_bounded_smoke_iteration_manifest.json`
- `local_asset_bounded_smoke_iteration_summary.md`
- `local_asset_bounded_smoke_iteration_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All expected iteration outputs are exclusive writes. Existing files or an
existing `smoke/` directory block execution.

## Artifact Index Relationship

The iteration artifact index includes explicit iteration artifact roles:

- `local_asset_bounded_smoke_iteration_result`
- `local_asset_bounded_smoke_iteration_manifest`
- `local_asset_bounded_smoke_iteration_summary`
- `local_asset_bounded_smoke_iteration_human_review_checklist`
- `local_asset_bounded_smoke_iteration_signoff`
- `local_asset_bounded_smoke_iteration_admission`

When delegated smoke artifacts exist, it also references the delegated smoke
root artifact index and manifest. It does not recursively index candidate
input files or recursively crawl smoke output contents.

## Task Graph Relationship

Task graph support was added under:

- `adapter_id = local_asset_runtime`
- `capability = launch_local_asset_bounded_smoke_iteration`

The task graph node exposes iteration artifact paths, status, decision,
bounded iteration flags, required human approval, and no-scope-expansion flags.
`task_graph_artifact_outputs.py` binds the new iteration artifact roles into
`task_graph_artifact_outputs.json`.

The adapter registry exposes the new capability under the existing
`local_asset_runtime` adapter. The adapter remains local-readonly /
controlled-output only and does not add external runtime permissions.

## Failure Behavior

- Missing `output_dir` returns a structured failure payload and writes no
  artifacts.
- Existing iteration outputs or `smoke/` block execution before any write.
- Unsafe overlap with input, promotion, review, or smoke outputs blocks
  execution without mutating those paths.
- Missing or invalid promotion output writes blocked iteration artifacts only
  when the iteration output directory is safe.
- Invalid signoff writes `signoff_valid=false`, `admitted=false`, blocked
  result artifacts, and does not create `smoke/`.
- Blocked promotion gate writes blocked result artifacts and does not create
  `smoke/`.
- Delegated smoke failure is recorded as `iteration_failed_smoke_run`.

## Deterministic Ordering Strategy

Artifact records, source artifacts, blockers, and role lists are sorted by
stable role names. JSON outputs use sorted keys and stable explicit path lists.
Deterministic comparison excludes absolute paths and file hashes where those
represent run-specific output roots.

## Explicit Non-Goals

- No production approval.
- No production promotion.
- No production scan approval.
- No automatic approval.
- No watcher or daemon.
- No UI.
- No Operator Console behavior.
- No network access.
- No model API calls.
- No external runtime invocation.
- No HFX change.
- No input mutation.
- No file movement, rename, or delete.
- No duplicate deletion.
- No media organizer behavior.
- No production autonomy.

## Validation Commands Run

- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_iteration -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`
- `python3 -m unittest discover -s tests/schemas -v`
- `python3 -m unittest discover -s validation/tests/acceptance -v`
- `python3 -m unittest discover -s tests/tracer_bullet -v`
- `python3 -m unittest tests.personal_ai.test_product_health_check -v`
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v`
- `make ci`
- `git diff --check`
- `git status --short`

All targeted unittest commands passed. The pre-commit `make ci` run passed
the test suite and then stopped at the clean-worktree guard because the
intended branch files were still uncommitted; the post-commit clean-worktree
`make ci` result below is the final CI gate.

## Final Validation Results

- Final post-commit `make ci` result: passed on a clean worktree.
- Final `git diff --check` result: passed with no output.
- Final `git status --short` result: clean.
- Final branch verification state: `feat/local-asset-bounded-smoke-iteration-v1`
  in the canonical local repository, ready for diff review.

## Next Recommended Branch

`feat/local-asset-smoke-iteration-review-packet-v1`
