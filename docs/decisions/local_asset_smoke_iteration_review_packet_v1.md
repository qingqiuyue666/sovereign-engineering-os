# Local Asset Smoke Iteration Review Packet v1

Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`

Canonical local repository path:
`<repo-root>`

Branch name: `feat/local-asset-smoke-iteration-review-packet-v1`

## Objective

Add a compact human review packet generator for outputs produced by local
asset bounded smoke iteration. The new layer consumes generated bounded
iteration artifacts and delegated smoke artifacts, then writes a separate
non-authoritative iteration review packet output directory.

This is not production scanning, not production promotion, and not automatic
approval.

## Changed Files

- `kernel/assets/local_asset_smoke_iteration_review_packet.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_smoke_iteration_review_packet.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_smoke_iteration_review_packet_v1.md`

## Behavior Added

The new capability adds the chain:

`bounded smoke iteration -> iteration review packet`

It summarizes outer iteration signoff, admission, promotion gate validation,
delegated human smoke state, delegated scan state, quarantine, duplicates,
SQLite manifest/query state, incremental plan state, failure state, warning
state, generated source artifacts, and a next human decision checklist.

## CLI Command

`launch-local-asset-smoke-iteration-review-packet`

Required arguments:

- `--iteration-output-dir`
- `--output-dir`

Optional argument:

- `--project-id`

The output directory must already exist and is never created automatically.

## Iteration Review Packet Artifact Schema

The primary packet is
`local_asset_smoke_iteration_review_packet.json` with:

- `packet_type = local_asset_smoke_iteration_review_packet_v1`
- `authority = non_authority`
- `execution_capability = local_asset_smoke_iteration_review_packet_only`
- `iteration_output_dir`
- `output_dir`
- `project_id`
- `iteration_review_status`
- `recommended_human_decision`
- `iteration_summary`
- `signoff_summary`
- `admission_summary`
- `promotion_summary`
- `delegated_smoke_summary`
- `delegated_scan_summary`
- `artifact_summary`
- `duplicate_summary`
- `quarantine_summary`
- `sqlite_summary`
- `incremental_summary`
- `failure_summary`
- `warning_summary`
- `decision_checklist`
- `source_artifacts`
- `missing_artifacts`
- `untrusted_artifacts`
- generated artifact read and missing counts
- deterministic ordering and explicit no-scope-expansion flags
- `required_human_approval = true`
- `next_allowed_action = human_review_smoke_iteration_review_packet`

The manifest is
`local_asset_smoke_iteration_review_packet_manifest.json` with packet,
summary, and checklist hashes plus generated source artifact path, SHA-256,
size, existence, required, and trusted-generated-artifact metadata.

## Source Artifact Policy

The module reads only a fixed allowlist of generated artifacts under the
bounded iteration output root. It may hash generated artifact files only. It
does not recursively discover private candidate input files, does not read
candidate raw file contents, does not hash candidate input files, and does
not copy raw private content.

## Required Vs Optional Artifacts

Required generated artifacts:

- `local_asset_bounded_smoke_iteration_result.json`
- `local_asset_bounded_smoke_iteration_manifest.json`
- `control/local_asset_bounded_smoke_iteration_signoff.json`
- `control/local_asset_bounded_smoke_iteration_admission.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated artifacts include the iteration summary/checklist,
delegated smoke root artifact index and manifest, delegated human smoke
approval and admission artifacts, delegated scan reports, generated SQLite
artifacts, generated incremental scan artifacts, and generated scan failure
artifacts.

If required artifacts are missing, the packet status is
`review_blocked_missing_required_artifacts` and the recommended human
decision is `reject_and_repair_iteration`.

## Summary Logic

The packet derives iteration status, decision, bounded limits, recursive
mode, include-hidden mode, and previous scan output directory from generated
iteration result/admission artifacts.

It derives signoff validity and phrase non-persistence from the generated
signoff artifact, without copying the signoff phrase plaintext into the
packet, manifest, summary, or checklist.

It derives promotion status and decision from the generated iteration result
and admission artifacts. Production promotion, production scan approval, and
production scan execution remain explicit false values.

It derives delegated smoke state from generated smoke approval and admission
artifacts. The delegated approval phrase plaintext is not persisted or copied.

It derives scan counts from generated scan receipt, manifest, validation, and
report artifacts. It derives duplicate and quarantine counts without
suggesting deletion. It derives SQLite row counts from the generated SQLite
manifest only and does not open candidate files or use global database state.
It derives incremental plan mode and changed/new/missing/suspicious counts
from the generated incremental plan only.

Failure summary copies only safe, bounded failure metadata. Raw tracebacks
are not copied and secret values are not serialized.

## Recommended Human Decision Rules

- Missing required artifacts:
  `review_blocked_missing_required_artifacts`,
  `reject_and_repair_iteration`.
- Untrusted generated artifacts, malformed required JSON, type mismatches, or
  manifest hash mismatches:
  `review_blocked_untrusted_artifacts`,
  `reject_and_repair_iteration`.
- Iteration status other than `iteration_completed`, or incomplete scan:
  `review_blocked_failed_iteration`,
  `reject_and_repair_iteration`.
- Quarantine count greater than zero:
  `review_ready_with_warnings`,
  `inspect_iteration_quarantine_before_promotion`.
- Duplicate group count greater than zero:
  `review_ready_with_warnings`,
  `inspect_iteration_duplicates_before_promotion`.
- Suspicious incremental changes, or changed/new/missing counts in
  compare-previous-scan mode:
  `review_ready_with_warnings`,
  `inspect_iteration_incremental_changes_before_promotion`.
- Otherwise:
  `review_ready`,
  `generate_promotion_gate_for_iteration`.

The packet never recommends production scan.

## Human Decision Checklist Logic

The checklist asks a human to verify iteration completion, promotion gate
scope, false production promotion/scan flags, signoff and delegated approval
phrase non-persistence, smoke launcher sequencing after valid gate and
signoff, bounded limits, scan completion, quarantine summary, duplicate
summary, SQLite summary, and incremental plan summary.

Decision options are:

- `generate_promotion_gate_for_iteration`
- `inspect_iteration_quarantine_before_promotion`
- `inspect_iteration_duplicates_before_promotion`
- `inspect_iteration_incremental_changes_before_promotion`
- `reject_and_repair_iteration`

The checklist does not include raw private file contents, does not suggest
deleting/moving/renaming files, does not suggest automatic dedupe, does not
grant production autonomy, and does not recommend production scan.

## Artifact Index Relationship

The review output directory gets its own explicit artifact index:

- `artifact_index.json`
- `artifact_index_manifest.json`

The index binds only:

- `local_asset_smoke_iteration_review_packet`
- `local_asset_smoke_iteration_review_packet_manifest`
- `local_asset_smoke_iteration_review_summary`
- `local_asset_smoke_iteration_human_decision_checklist`

It does not recursively index candidate input files and does not recursively
index iteration output files beyond the explicit generated review artifacts.

## Task Graph Relationship

The existing `local_asset_runtime` adapter exposes:

- `launch_local_asset_smoke_iteration_review_packet`

Task graph node inputs:

- `iteration_output_dir`
- `output_dir`
- `project_id`

Node execution records expose review packet artifact paths, iteration review
status, recommended human decision, iteration status, bounded iteration
status, smoke and scan completion, production false flags, review-packet
non-execution flags, and `required_human_approval = true`.

`task_graph_artifact_outputs.json` binds the review packet, manifest,
summary, and human decision checklist roles.

The adapter remains local-readonly / controlled-output only and does not add
external runtime permissions.

## Failure Behavior

- Existing expected review output files block execution and no review
  artifacts are written.
- Missing `output_dir` returns a structured failure payload, does not create
  the directory, and writes no artifacts.
- Unsafe directory overlap returns a structured failure payload and writes no
  artifacts.
- Missing required iteration artifacts in a safe existing `output_dir` writes
  a blocked review packet rather than pretending the iteration is ready.
- Untrusted generated artifacts or manifest hash mismatches block review
  readiness.
- The module does not mutate the iteration output root, delegated smoke
  output root, candidate input directory, or promotion output directory.

## Deterministic Ordering Strategy

Source artifact specs are fixed and sorted by artifact role. Missing
artifact roles, untrusted artifact roles, warning roles, source records,
artifact index entries, checklist decision options, and summary counts are
deterministic. Deterministic tests compare stable fields rather than absolute
paths or hashes that necessarily differ across run directories.

## Explicit Non-Behavior

- No scan performed.
- No readiness run performed.
- No human smoke run performed by the review packet.
- No bounded smoke iteration performed by the review packet.
- No promotion gate run performed.
- No raw candidate content read.
- No candidate file hashing.
- No iteration output mutation.
- No smoke output mutation.
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
- No production scan recommendation.

## Validation

Validation commands run before final commit:

- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_iteration_review_packet -v`
  passed, 13 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_bounded_smoke_iteration -v`
  passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v`
  passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v`
  passed, 11 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v`
  passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v`
  passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`
  passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`
  passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`
  passed, 8 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`
  passed, 7 tests.
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`
  passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`
  passed, 5 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`
  passed, 4 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`
  passed, 12 tests.
- `python3 -m unittest discover -s tests/schemas -v`
  passed, 133 tests.
- `python3 -m unittest discover -s validation/tests/acceptance -v`
  passed, 156 tests.
- `python3 -m unittest discover -s tests/tracer_bullet -v`
  passed, 6501 tests, 4 skipped.
- `python3 -m unittest tests.personal_ai.test_product_health_check -v`
  passed, 5 tests.
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v`
  passed, 8 tests.
- `make ci` ran test targets successfully, then failed its clean-tree
  diff-check because the intended branch changes were still uncommitted.
- `git diff --check` passed.
- `git status --short` showed only intended branch changes before commit.

Final post-commit `make ci` result: passed after commit.

Final `git diff --check` result: passed after commit.

Final `git status --short` result: clean after commit.

Final branch verification state: branch
`feat/local-asset-smoke-iteration-review-packet-v1` contained the committed
implementation and passed final validation.

## Next Recommended Branch

`feat/local-asset-iteration-promotion-gate-v1`
