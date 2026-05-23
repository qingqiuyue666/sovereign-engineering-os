# Local Asset Next Bounded Smoke Iteration Admission v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch: `feat/local-asset-next-bounded-smoke-iteration-admission-v1`

## Objective

Add a non-executing admission layer for preparing the next bounded smoke
iteration after a completed bounded smoke cycle human review. The layer
consumes generated cycle human review artifacts and emits a durable admission
receipt stating whether preparation of a future next bounded smoke iteration
execution request is admitted.

The layer is an admission/permission artifact only. It does not execute the
next bounded smoke iteration and does not create the next iteration output
directory.

## Changed Files

- `kernel/assets/local_asset_next_bounded_smoke_iteration_admission.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_next_bounded_smoke_iteration_admission.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_next_bounded_smoke_iteration_admission_v1.md`

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_iteration_admission(...)` and the CLI
command `launch-local-asset-next-bounded-smoke-iteration-admission`.

Required inputs:

- `cycle_human_review_output_dir`
- `output_dir`

Optional metadata:

- `project_id`
- `requested_next_iteration_id`
- `operator_notes`

The builder writes only to an existing, separate output directory. All writes
are exclusive. Missing output directories, existing output files, symlinked
output roots, and unsafe input/output overlap fail closed without writing
admission artifacts. If the cycle human review output directory is missing or
unsafe but the admission output directory is safe, the builder writes a
blocked admission artifact without creating or mutating the human review root.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-admission \
  --cycle-human-review-output-dir /path/to/cycle-human-review-output \
  --output-dir /path/to/next-admission-output \
  --project-id demo_project \
  --requested-next-iteration-id iteration-002 \
  --operator-notes "optional notes"
```

## Schema

The admission JSON uses `admission_type:
local_asset_next_bounded_smoke_iteration_admission_v1`, `authority:
non_authority_admission_record`, and `execution_capability:
local_asset_next_bounded_smoke_iteration_admission_only`.

It records project and path metadata, optional requested next iteration id,
optional operator notes, source human review fields, admission status,
admission decision, next allowed action, prepare admission, execute denial,
next-iteration execution/output flags, production denial, automatic approval
denial, autonomy denial, source artifact trust state, missing/untrusted
artifact lists, blockers, deterministic ordering, human approval/review
requirements, and explicit false boundary flags.

Admission status values:

- `next_bounded_smoke_iteration_admission_ready`
- `blocked_missing_required_artifacts`
- `blocked_untrusted_artifacts`
- `blocked_human_review_not_approved`
- `blocked_prepare_not_allowed`
- `blocked_execution_already_allowed`
- `blocked_production_boundary_violation`
- `blocked_invalid_human_review_record`
- `blocked_unknown`

Admission decision values:

- `admit_prepare_next_bounded_smoke_iteration`
- `reject_and_repair_artifacts`
- `reject_and_repair_human_review`
- `reject_boundary_violation`

Next allowed action values:

- `create_next_bounded_smoke_iteration_execution_request`
- `repair_artifacts`
- `repair_human_review`
- `reject_boundary_violation`

## Source Artifact Policy

The admission reads and hashes only generated artifacts in the declared cycle
human review output directory. It does not recursively index the cycle human
review output directory, the cycle contract output directory, upstream output
directories, or candidate input files. It does not read raw private content,
hash candidate input files, copy raw private content, or inspect candidate
payloads.

No human signoff phrase is accepted by this branch. No plaintext approval
phrase is handled by this branch. The admission consumes only the
already-recorded human review decision.

## Required Artifacts

Required generated cycle human review artifacts:

- `local_asset_bounded_smoke_cycle_human_review_decision.json`
- `local_asset_bounded_smoke_cycle_human_review_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated cycle human review artifacts are bound when present:

- `local_asset_bounded_smoke_cycle_human_review_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`

Trust checks verify expected generated artifact type fields, the human review
manifest decision hash, optional summary/checklist hashes when those files are
present, and the artifact index manifest hash for the human review artifact
index. Malformed JSON marks the source artifact untrusted.

## Admission Rules

Admission is ready only when all required generated human review artifacts
exist and are trusted; the human review decision artifact is approved for
next bounded smoke iteration preparation; `human_review_decision` is
`allow_prepare_next_bounded_smoke_iteration`; `human_decision` is
`approve_cycle_contract_for_next_bounded_smoke_iteration`; plaintext signoff
was not persisted; prepare is allowed; execute is denied; the cycle human
review next action is `prepare_next_bounded_smoke_iteration_admission`; the
required production/autonomy actions are disallowed; the cycle contract status
is `cycle_contract_ready` or `cycle_contract_ready_with_warnings`; and the
cycle contract decision binds the completed cycle without granting production.

When ready, the record emits:

- `admission_status: next_bounded_smoke_iteration_admission_ready`
- `admission_decision: admit_prepare_next_bounded_smoke_iteration`
- `next_allowed_action: create_next_bounded_smoke_iteration_execution_request`
- `next_bounded_smoke_iteration_prepare_admitted: true`
- `next_bounded_smoke_iteration_execute_allowed: false`
- `next_bounded_smoke_iteration_executed: false`
- `next_iteration_output_dir_created: false`

This admits creation of a future execution request only.

## Blocker Logic

Missing required artifacts map to `blocked_missing_required_artifacts`,
`reject_and_repair_artifacts`, and `repair_artifacts`.

Untrusted artifacts map to `blocked_untrusted_artifacts`,
`reject_and_repair_artifacts`, and `repair_artifacts`.

A non-approved human review maps to `blocked_human_review_not_approved`,
`reject_and_repair_human_review`, and `repair_human_review`.

Prepare denial maps to `blocked_prepare_not_allowed`,
`reject_and_repair_human_review`, and `repair_human_review`.

Existing execute permission maps to `blocked_execution_already_allowed`,
`reject_boundary_violation`, and `reject_boundary_violation`.

Production or mutation boundary violations map to
`blocked_production_boundary_violation`, `reject_boundary_violation`, and
`reject_boundary_violation`.

Malformed or internally inconsistent human review records map to
`blocked_invalid_human_review_record`, `reject_and_repair_human_review`, and
`repair_human_review`.

## Artifact Index Relationship

The admission `artifact_index.json` binds only the four admission artifacts:

- `local_asset_next_bounded_smoke_iteration_admission`
- `local_asset_next_bounded_smoke_iteration_admission_manifest`
- `local_asset_next_bounded_smoke_iteration_admission_summary`
- `local_asset_next_bounded_smoke_iteration_admission_checklist`

It does not recursively index the cycle human review output directory, cycle
contract output directory, upstream output roots, or candidate input files.

The admission manifest records hashes for the admission JSON, summary,
checklist, and named source generated human review artifacts.

## Task Graph Relationship

The local asset task graph supports `adapter_id: local_asset_runtime` with
`capability: launch_local_asset_next_bounded_smoke_iteration_admission`. The
node exposes admission paths, admission status, admission decision, next
allowed action, prepare admission, execute denial, next-iteration execution
denial, next output directory denial, human approval/review requirements, and
explicit false boundary flags.

`task_graph_artifact_outputs.py` binds the four admission artifact roles:

- `local_asset_next_bounded_smoke_iteration_admission`
- `local_asset_next_bounded_smoke_iteration_admission_manifest`
- `local_asset_next_bounded_smoke_iteration_admission_summary`
- `local_asset_next_bounded_smoke_iteration_admission_checklist`

## Failure Behavior

The builder writes no artifacts when the admission output directory is missing
or unsafe, when an expected admission output file already exists, or when the
cycle human review output directory and admission output directory overlap.

If the source human review directory is missing or unsafe but the output
directory is safe and separate, the builder writes a blocked admission receipt.
It does not create, mutate, move, rename, delete, or deduplicate upstream
artifacts.

## Deterministic Ordering

Source artifact records are sorted deterministically by artifact role.
Admission artifact index entries use a fixed role order. JSON outputs are
written with sorted keys. Stable decision fields and checklist items remain
deterministic across equivalent runs.

## Explicit Non-Behavior

- No scan execution.
- No readiness execution.
- No human smoke execution.
- No smoke review packet execution.
- No smoke promotion gate execution.
- No bounded smoke iteration execution.
- No iteration review packet execution.
- No iteration promotion gate execution.
- No cycle contract generation.
- No cycle human review generation.
- No next bounded smoke iteration execution.
- No next iteration output directory creation.
- No production scan approval.
- No production promotion.
- No automatic approval.
- No autonomous execution.
- No candidate raw content read.
- No candidate file hashing.
- No candidate input mutation.
- No upstream output mutation.
- No file move, rename, delete, or dedupe.
- No duplicate deletion.
- No media organizer behavior.
- No watcher or daemon behavior.
- No UI or Operator Console.
- No global database state.
- No network access.
- No model API calls.
- No external creative runtime invocation.
- No HFX modification.

## Validation Commands

- `python3 -m unittest tests.tracer_bullet.test_local_asset_next_bounded_smoke_iteration_admission -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_human_review -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_cycle_contract -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_iteration_promotion_gate -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_iteration_review_packet -v`
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

## Final Validation State

- Required unittest battery result: PASS.
- Pre-commit `make ci` result: test suites and `git diff --check` passed; the
  final clean-worktree guard failed because the branch changes were
  intentionally uncommitted before the requested commit step.
- Final post-commit `make ci` result: PASS.
- Final `git diff --check` result: PASS.
- Final `git status --short` result: clean after commit.
- Final branch verification state: branch
  `feat/local-asset-next-bounded-smoke-iteration-admission-v1` pushed, draft
  PR #410 opened against main, post-commit validation passed, final
  `git diff --check` passed, and final `git status --short` was clean.

## Next Recommended Branch

Recommended next branch:
`feat/local-asset-next-bounded-smoke-iteration-execution-request-v1`

The next branch should create an explicit future execution request artifact
from a ready admission receipt. It should still avoid executing the next
bounded smoke iteration until a separate runtime branch consumes that request
under bounded limits and human controls.
