# Local Asset Next Bounded Smoke Iteration Run Review Packet v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`<repo-root>`

Branch:
`feat/local-asset-next-bounded-smoke-iteration-run-review-packet-v1`

## Objective

Add a non-executing review packet layer for the actual next bounded smoke
iteration run produced by the runner. The packet consumes generated runner
artifacts and generated actual next iteration artifacts, verifies generated
type and hash bindings, checks cross-artifact consistency, and emits durable
review artifacts for a later separate promotion gate.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_run_review_packet.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_run_review_packet.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_run_review_packet_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_run_review_packet(...)`, the
launcher
`run_local_asset_next_bounded_smoke_iteration_run_review_packet_launcher(...)`,
the CLI command
`launch-local-asset-next-bounded-smoke-iteration-run-review-packet`, and task
graph support for capability
`launch_local_asset_next_bounded_smoke_iteration_run_review_packet`.

Required builder inputs are `runner_output_dir`,
`actual_next_iteration_output_dir`, `output_dir`, and `review_packet_id`.
Optional metadata is `project_id`, `reviewer_id`, and `operator_notes`.

The builder does not execute the runner, discover candidates, validate live
candidate paths, list candidate directories, read candidate files, hash live
candidate files, mutate upstream outputs, or approve promotion or production.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-run-review-packet \
  --runner-output-dir /path/to/runner-output \
  --actual-next-iteration-output-dir /path/to/actual-next-iteration-output \
  --output-dir /path/to/run-review-output \
  --review-packet-id run-review-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

## Schema

The review packet JSON uses `review_packet_type:
local_asset_next_bounded_smoke_iteration_run_review_packet_v1`, `authority:
non_authority_review_packet_record`, and `execution_capability:
local_asset_next_bounded_smoke_iteration_run_review_packet_only`.

It records review packet metadata, inherited runner and request metadata,
source runner status and candidate metadata, review status, review decision,
next allowed action, source artifact refs, missing required artifacts,
untrusted artifacts, cross-artifact checks, blockers, deterministic ordering,
human approval/review requirements, disallowed actions, and explicit false
boundary flags.

The manifest uses `manifest_type:
local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_v1` and
binds the packet, summary, checklist, source artifact refs, hashes, review
status, review decision, next allowed action, and explicit false boundary
flags.

## Source Artifact Policy

The review packet reads only generated source artifacts by explicit filename.
It does not recursively index source directories and does not touch
`requested_candidate_input_dir` except as inert string metadata inherited from
generated artifacts.

Required runner source artifacts:

- `local_asset_next_bounded_smoke_iteration_runner.json`
- `local_asset_next_bounded_smoke_iteration_runner_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional runner source artifacts:

- `local_asset_next_bounded_smoke_iteration_runner_summary.md`
- `local_asset_next_bounded_smoke_iteration_runner_checklist.md`

Required actual iteration source artifacts:

- `local_asset_next_bounded_smoke_iteration_run.json`
- `local_asset_next_bounded_smoke_iteration_run_manifest.json`
- `local_asset_next_bounded_smoke_iteration_candidate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional actual iteration source artifacts:

- `local_asset_next_bounded_smoke_iteration_summary.md`
- `local_asset_next_bounded_smoke_iteration_checklist.md`

Malformed JSON is untrusted. Source artifact type fields and manifest hashes
must match the expected generated artifact contracts.

## Required Artifacts

The review packet output directory must already exist. It receives:

- `local_asset_next_bounded_smoke_iteration_run_review_packet.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed on existing files.

## Review Readiness Rules

The packet is ready only when the runner and actual run artifacts report
`next_bounded_smoke_iteration_runner_completed`,
`executed_bounded_smoke_iteration_under_admitted_limits`, and
`review_next_bounded_smoke_iteration_run`; runner execution and next bounded
smoke iteration execution are true; output directory creation flags are false;
candidate limits are enforced; source production, mutation, media organizer,
network, model, external runtime, automatic approval, and autonomy flags are
false; candidate symlinks are empty; candidate records are deterministic
metadata-only records; required generated artifacts exist; source artifacts
are trusted; and no blockers are present.

When ready, `review_status` is
`next_bounded_smoke_iteration_run_review_packet_ready`,
`review_decision` is
`package_next_bounded_smoke_iteration_run_for_promotion_gate_review`, and
`next_allowed_action` is
`run_next_bounded_smoke_iteration_run_promotion_gate`.

## Cross-Artifact Consistency Rules

The review packet checks that runner and run metadata match for runner
execution id, runner operator id, runner admission id, requested next
iteration id when present, requested candidate input dir, requested next
iteration output dir, requested limits, admitted limits, candidate file count,
candidate total bytes, candidate max depth observed, and bounded file records.

It also checks that `actual_next_iteration_output_dir` in the actual run
record matches the input path and that `actual_iteration_artifacts` listed in
the runner manifest correspond to generated actual iteration files by role,
path, size, and SHA-256.

## Blocker Logic

Missing required generated artifacts produce
`blocked_missing_required_artifacts`. Untrusted generated artifacts produce
`blocked_untrusted_artifacts`. Runner completion failures produce
`blocked_runner_not_completed`. Invalid actual run records produce
`blocked_invalid_actual_run_record`. Invalid candidate manifests produce
`blocked_invalid_candidate_manifest`. Cross-artifact mismatches produce
`blocked_cross_artifact_inconsistency`. Source boundary violations produce
`blocked_source_boundary_violation`. Invalid review packet metadata produces
`blocked_invalid_review_packet_metadata`.

## Generated-Artifacts-Only Policy

The review packet never scans candidate input directories and never stats,
reads, or hashes candidate input files. Candidate metadata is consumed only
from generated runner, run, and candidate manifest artifacts.

## No Live Candidate Access Policy

The review packet reports
`candidate_input_path_checked_by_review=false`,
`candidate_input_path_listed_by_review=false`,
`candidate_input_file_read_by_review=false`, and
`candidate_input_file_hashing_performed_by_review=false` in the payload,
packet, manifest, and task graph node record.

## Artifact Index Relationship

The local output `artifact_index.json` binds only the review packet, review
packet manifest, summary, and checklist. It does not recursively index
runner output, actual iteration output, upstream cycle outputs, or candidate
input files.

## Task Graph Relationship

The local asset adapter registry admits
`launch_local_asset_next_bounded_smoke_iteration_run_review_packet`. Task
graph execution records the review packet artifact paths, review status,
review decision, next allowed action, inherited runner/request metadata, human
approval/review requirements, and explicit false boundary flags. Task graph
artifact output binding adds the four review packet roles.

## Failure Behavior

If `output_dir` is missing, unsafe, overlapping, or already contains expected
review output files, the builder returns a structured failure and writes no
artifacts. If source directories are missing or unsafe while `output_dir` is
safe, it writes a blocked review packet artifact without creating or mutating
source directories.

## Deterministic Ordering

Source artifacts are sorted by role. Candidate bounded records must already
be sorted by `relative_path`. Checklist items, disallowed actions, source
artifact roles, and cross-artifact checks are emitted in stable order.

## Explicit Non-Behavior

This branch does not run readiness, human smoke, smoke review, smoke
promotion, bounded smoke iteration, iteration review, iteration promotion,
cycle contract, cycle human review, next admission, execution request, runner
admission, or runner execution. It does not scan candidate inputs, validate
live candidate paths, list candidate directories, read raw candidate content,
hash live candidate files, create source output directories, move files,
rename files, delete files, deduplicate files, add media organizer behavior,
copy raw private content, upload anything, call model APIs, use network
access, invoke external creative runtimes, add watcher/daemon behavior, add
UI or Operator Console behavior, add global database state, approve
promotion, approve production scanning, grant production promotion, or grant
autonomy.

## Validation Commands

```bash
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

## Final Validation Results

- Final post-commit `make ci` result: passed on a clean committed
  worktree.
- Final `git diff --check` result: passed.
- Final `git status --short` result: clean after validation.
- Final branch verification state: branch was verified on
  `feat/local-asset-next-bounded-smoke-iteration-run-review-packet-v1`
  after the review packet commit.

## Next Recommended Branch

Add the separate next bounded smoke iteration run promotion gate that consumes
this review packet without approving production scanning or production
promotion.
