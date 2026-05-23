# Local Asset Iteration Promotion Gate v1

## Repository

- Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`
- Canonical local repository path: `/Users/qqy/Documents/GitHub/sovereign-engineering-os`
- Branch name: `feat/local-asset-iteration-promotion-gate-v1`

## Objective

Add a non-authoritative promotion gate for local asset smoke iteration review
packets. The gate consumes generated iteration review packet artifacts only
and decides whether a clean reviewed iteration is eligible for the next
bounded smoke iteration. It does not approve production scanning or grant
production promotion.

## Changed Files

- `kernel/assets/local_asset_iteration_promotion_gate.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_iteration_promotion_gate.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_iteration_promotion_gate_v1.md`

## Behavior Added

The new capability adds the chain:

`iteration review packet -> iteration promotion gate`

It writes a separate promotion output directory with a decision artifact,
gate manifest, summary, human signoff checklist, and explicit artifact index.
The decision is deterministic, metadata-only, non-authoritative, and always
requires human review.

## CLI Command

`launch-local-asset-iteration-promotion-gate`

Required arguments:

- `--iteration-review-output-dir`
- `--output-dir`

Optional argument:

- `--project-id`

The output directory must already exist. The command does not create it.

## Iteration Promotion Decision Artifact Schema

The primary decision artifact is
`local_asset_iteration_promotion_decision.json` with:

- `decision_type = local_asset_iteration_promotion_decision_v1`
- `authority = non_authority`
- `execution_capability = local_asset_iteration_promotion_gate_only`
- `iteration_review_output_dir`, `output_dir`, and `project_id`
- `iteration_promotion_gate_status`
- `iteration_promotion_decision`
- `next_bounded_smoke_iteration_allowed`
- `production_promotion_granted = false`
- `production_scan_approved = false`
- `production_scan_performed = false`
- iteration review status and recommended human decision
- iteration, signoff, admission, promotion, delegated smoke, delegated scan,
  duplicate, quarantine, SQLite, incremental, failure, warning, and blocker
  summaries
- iteration promotion blockers, allowed next action, and rejected next actions
- human signoff checklist
- source artifacts, missing iteration review artifacts, and untrusted
  iteration review artifacts
- deterministic ordering and explicit false no-scope-expansion flags
- `required_human_approval = true`
- `next_allowed_action = human_review_iteration_promotion_gate`

## Source Artifact Policy

The module reads only generated iteration review packet artifacts from the
iteration review output directory. It may hash generated iteration review
packet artifact files only. It never recursively discovers private candidate
input files, never reads candidate raw file contents, never hashes candidate
input files, and never copies raw private content.

## Required Vs Optional Iteration Review Artifacts

Required generated artifacts:

- `local_asset_smoke_iteration_review_packet.json`
- `local_asset_smoke_iteration_review_packet_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated artifacts:

- `local_asset_smoke_iteration_review_summary.md`
- `local_asset_smoke_iteration_human_decision_checklist.md`

Missing required artifacts produce
`iteration_promotion_gate_status = blocked_missing_iteration_review_artifacts`
and do not allow the next bounded smoke iteration.

## Gate Decision Rules

The only allowed promotion decision is
`allow_next_bounded_smoke_iteration`, and it is emitted only when all clean
iteration review conditions are true:

- iteration review packet exists and is trusted
- packet manifest exists and hashes match where applicable
- artifact index exists and artifact index manifest hash matches
- iteration review status is `review_ready`
- iteration review recommended human decision is
  `generate_promotion_gate_for_iteration`
- iteration status is `iteration_completed`
- bounded smoke iteration was performed
- smoke run is complete
- scan is complete
- production promotion, production scan approval, and production scan
  execution are false
- input mutation and duplicate deletion are false
- quarantine count is zero
- duplicate group count is zero
- suspicious incremental change count is zero
- no blocking warning is present
- no required generated artifact is missing
- no generated artifact is untrusted

The gate never produces production approval and never recommends production
scan.

## Blocker Logic

- Quarantine produces `blocked_quarantine` and
  `block_until_human_inspects_iteration_quarantine`.
- Duplicate groups produce `blocked_duplicates` and
  `block_until_human_inspects_iteration_duplicates`.
- Incremental changes that require inspection produce
  `blocked_incremental_changes` and
  `block_until_human_inspects_iteration_incremental_changes`.
- Failed or incomplete iteration state produces `blocked_failed_iteration`
  and `block_until_iteration_repaired`.
- Missing generated iteration review artifacts produce
  `blocked_missing_iteration_review_artifacts` and
  `block_until_iteration_review_packet_repaired`.
- Untrusted, malformed, type-mismatched, or hash-mismatched generated
  iteration review artifacts produce
  `blocked_untrusted_iteration_review_packet` and
  `block_until_iteration_review_packet_repaired`.
- Blocking warnings produce `blocked_warnings` and
  `block_until_iteration_review_packet_repaired`.

## Human Signoff Checklist Logic

The checklist asks a human to verify iteration review readiness, recommended
decision, iteration completion, bounded smoke iteration execution, smoke
completion, scan completion, false production promotion and production scan
flags, false input mutation and duplicate deletion flags, zero quarantine
count, zero duplicate group count, zero suspicious incremental changes, no
blocker, and that the next action is only another bounded smoke iteration.

Signoff options are:

- `approve_next_bounded_smoke_iteration`
- `reject_and_repair_iteration_review_packet`
- `reject_and_repair_iteration`
- `inspect_iteration_quarantine`
- `inspect_iteration_duplicates`
- `inspect_iteration_incremental_changes`

The checklist does not include raw private file contents, does not suggest
moving, renaming, deleting, or deduplicating files, does not grant production
autonomy, and does not recommend production scan.

## Artifact Index Relationship

The promotion output directory gets its own explicit artifact index:

- `artifact_index.json`
- `artifact_index_manifest.json`

The index binds only:

- `local_asset_iteration_promotion_decision`
- `local_asset_iteration_promotion_gate_manifest`
- `local_asset_iteration_promotion_summary`
- `local_asset_iteration_promotion_human_signoff_checklist`

It does not recursively index candidate input files and does not recursively
index iteration review output files beyond the explicit generated promotion
artifacts.

## Task Graph Relationship

The existing `local_asset_runtime` adapter exposes
`launch_local_asset_iteration_promotion_gate`. Task graph nodes accept
`iteration_review_output_dir`, `output_dir`, and optional `project_id`.
Node execution records expose the promotion decision paths, status, blocker
state, explicit false no-scope-expansion flags, and production approval flags.

`task_graph_artifact_outputs.json` binds the iteration promotion decision,
gate manifest, summary, and human signoff checklist roles.

## Failure Behavior

The promotion output files are exclusive writes. If any expected promotion
output file already exists, the command returns a structured failure payload
and writes no promotion artifacts. If the output directory is missing, it is
not created. If the iteration review output root is missing or lacks required
generated artifacts, a safe existing output directory can receive a blocked
promotion decision. If directories overlap unsafely, including upstream
directories discoverable from the generated review packet, the command
returns a structured failure payload and writes no artifacts.

## Deterministic Ordering Strategy

Source artifact specs are fixed and sorted by artifact role. Missing artifact
roles, untrusted artifact roles, blocker roles, rejected next actions,
artifact index entries, checklist items, and signoff options are
deterministic. Tests compare stable fields without relying on absolute path
or generated hash equality.

## Explicit Non-Behavior

- No scan performed.
- No readiness run performed.
- No human smoke run performed.
- No bounded smoke iteration performed by gate.
- No iteration review packet run performed.
- No raw candidate content read.
- No candidate file hashing.
- No iteration review output mutation.
- No iteration output mutation.
- No delegated smoke output mutation.
- No input mutation.
- No file movement, rename, or delete.
- No duplicate deletion.
- No media organizer behavior.
- No watcher or daemon.
- No global database state.
- No UI.
- No Operator Console.
- No network.
- No model API.
- No external runtime.
- No HFX change.
- No production autonomy.
- No production scan approval.
- No production scan recommendation.

## Validation

Validation commands run:

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

Pre-commit `make ci` result: test body passed, then the final Makefile
clean-worktree check failed because this branch intentionally had uncommitted
changes before the required commit step.

Pre-commit `git diff --check` result: pass.

Pre-commit `git status --short` result: intended branch files modified and
new, with no unrelated files observed.

Final post-commit `make ci` result: pass.

Final `git diff --check` result: pass.

Final `git status --short` result: clean.

Final branch verification state: branch committed, post-commit validation
passed, pending push and pull request creation.

## Next Recommended Branch

`feat/local-asset-bounded-smoke-cycle-contract-v1`
