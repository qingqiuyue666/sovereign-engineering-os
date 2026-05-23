# Local Asset Bounded Smoke Cycle Human Review v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch: `feat/local-asset-bounded-smoke-cycle-human-review-v1`

## Objective

Add a durable human review decision layer for the local asset bounded smoke
cycle contract. The layer consumes generated cycle contract artifacts plus
explicit human review inputs, validates the human signoff phrase, stores only
the phrase hash, and records whether preparation of the next bounded smoke
iteration admission may proceed.

The layer is a review record only. It does not run scan, readiness, human
smoke, review generation, promotion gates, bounded iteration, iteration
review, iteration promotion, or cycle contract generation.

## Changed Files

- `kernel/assets/local_asset_bounded_smoke_cycle_human_review.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_bounded_smoke_cycle_human_review.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_bounded_smoke_cycle_human_review_v1.md`

## Behavior Added

The branch adds `build_local_asset_bounded_smoke_cycle_human_review(...)` and
the CLI command `launch-local-asset-bounded-smoke-cycle-human-review`. The
builder requires a generated cycle contract output directory, a pre-existing
review output directory, explicit human review identity, an allowed human
decision, and the exact human signoff phrase.

It writes:

- `local_asset_bounded_smoke_cycle_human_review_decision.json`
- `local_asset_bounded_smoke_cycle_human_review_manifest.json`
- `local_asset_bounded_smoke_cycle_human_review_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive. Missing output directories, existing output files,
symlinked output roots, empty human review identity fields, and unsafe
input/output overlap fail closed without writing review artifacts.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-bounded-smoke-cycle-human-review \
  --cycle-contract-output-dir /path/to/cycle-contract-output \
  --output-dir /path/to/cycle-human-review-output \
  --human-review-id review-001 \
  --human-reviewer-id reviewer-001 \
  --human-decision approve_cycle_contract_for_next_bounded_smoke_iteration \
  --human-signoff-phrase I_REVIEWED_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT \
  --project-id demo_project \
  --human-review-notes "optional notes"
```

## Schema

The decision JSON uses `decision_type:
local_asset_bounded_smoke_cycle_human_review_decision_v1`, `authority:
human_review_record`, and `execution_capability:
local_asset_bounded_smoke_cycle_human_review_only`.

It records `project_id`, `cycle_contract_output_dir`, `output_dir`,
`human_review_id`, `human_reviewer_id`, the supplied `human_decision`, the
SHA-256 hash of the signoff phrase, note presence, optional review notes,
cycle contract status and decision fields, source artifact trust state,
missing/untrusted artifact lists, human review status and decision, prepare
and execute allowance flags, next allowed action, disallowed actions,
deterministic ordering, explicit false boundary flags, and human review
requirements.

Human review status values:

- `human_review_approved_next_bounded_smoke_iteration`
- `human_review_stopped_cycle`
- `human_review_requires_artifact_repair`
- `human_review_requires_cycle_repair`
- `human_review_requires_quarantine_inspection`
- `human_review_requires_duplicate_inspection`
- `human_review_requires_incremental_inspection`
- `human_review_rejected_boundary_violation`
- `blocked_invalid_human_signoff`
- `blocked_invalid_human_decision`
- `blocked_missing_required_artifacts`
- `blocked_untrusted_artifacts`
- `blocked_cycle_contract_not_ready`
- `blocked_cycle_contract_boundary_violation`
- `blocked_unknown`

Human review decision values:

- `allow_prepare_next_bounded_smoke_iteration`
- `stop_cycle`
- `repair_artifacts`
- `repair_cycle`
- `inspect_quarantine`
- `inspect_duplicates`
- `inspect_incremental_changes`
- `reject_boundary_violation`
- `reject_and_repair_human_review`

## Source Artifact Policy

The review reads and hashes only generated artifacts in the declared cycle
contract output directory. It does not recursively index the cycle contract
directory, upstream output directories, or candidate input files. It does not
read raw private content, hash candidate inputs, or copy raw private content.

## Required Artifacts

Required generated cycle contract artifacts:

- `local_asset_bounded_smoke_cycle_contract.json`
- `local_asset_bounded_smoke_cycle_contract_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated cycle contract artifacts are bound when present:

- `local_asset_bounded_smoke_cycle_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`

The review verifies expected artifact types, the cycle contract manifest hash
for the contract and optional markdown artifacts when present, and the artifact
index manifest hash for the cycle artifact index.

## Human Decision Mapping

`approve_cycle_contract_for_next_bounded_smoke_iteration` maps to
`human_review_approved_next_bounded_smoke_iteration` and
`allow_prepare_next_bounded_smoke_iteration` only when all approval rules pass.

`stop_cycle`, `repair_artifacts`, `repair_cycle`, `inspect_quarantine`,
`inspect_duplicates`, `inspect_incremental_changes`, and
`reject_boundary_violation` map directly to their corresponding human review
statuses and next allowed actions. None of those decisions allow preparation
or execution of the next bounded smoke iteration.

Invalid human decisions map to `blocked_invalid_human_decision` and
`reject_and_repair_human_review`. Invalid signoff maps to
`blocked_invalid_human_signoff` and `reject_and_repair_human_review`.

## Approval Rules

Preparation of the next bounded smoke iteration admission is allowed only when
the exact signoff phrase is supplied, the human decision is
`approve_cycle_contract_for_next_bounded_smoke_iteration`, the cycle contract
and its manifest are trusted, the cycle artifact index and manifest are
trusted, the cycle contract status is ready or allowed ready-with-warnings,
the cycle contract decision binds the completed cycle, the cycle contract next
allowed action is `human_review_bounded_smoke_cycle_contract`, production scan
and production promotion are disallowed by the cycle contract, human review is
required, no cycle blockers exist, no required artifacts are missing, no
artifacts are untrusted, and no production or mutation boundary violation is
present.

When approved, the review emits
`next_allowed_action: prepare_next_bounded_smoke_iteration_admission`,
`next_bounded_smoke_iteration_prepare_allowed: true`, and
`next_bounded_smoke_iteration_execute_allowed: false`.

## Phrase Hash-Only Policy

The required phrase is
`I_REVIEWED_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT`. The builder validates
that phrase exactly and stores only `human_signoff_phrase_sha256`. It sets
`human_signoff_phrase_persisted: false` and does not write the plaintext
phrase into the decision, manifest, summary, checklist, or artifact index.

## Artifact Index Relationship

The review `artifact_index.json` binds only the four human review artifacts:
decision, review manifest, summary, and review checklist. It does not
recursively index the cycle contract output directory, upstream output roots,
or candidate input files.

The review manifest records hashes for the decision, summary, checklist, and
source generated cycle contract artifacts.

## Task Graph Relationship

The local asset task graph supports `adapter_id: local_asset_runtime` with
`capability: launch_local_asset_bounded_smoke_cycle_human_review`. The node
exposes review decision paths, human review status, human review decision,
next allowed action, prepare allowance, execute denial, human review flags,
and explicit false boundary flags.

`task_graph_artifact_outputs.py` binds the four review artifact roles:

- `local_asset_bounded_smoke_cycle_human_review_decision`
- `local_asset_bounded_smoke_cycle_human_review_manifest`
- `local_asset_bounded_smoke_cycle_human_review_summary`
- `local_asset_bounded_smoke_cycle_human_review_checklist`

## Failure Behavior

The builder fails closed before writing artifacts when the review output
directory is missing, a review output file already exists, human review ids are
empty, or roots overlap unsafely. If the cycle contract output directory is
missing or unsafe but the review output directory is safe, the builder writes a
blocked review artifact without creating or mutating the cycle contract root.

Missing or untrusted generated cycle contract artifacts produce blocked review
artifacts. Invalid signoff and invalid human decisions also produce blocked
review artifacts when output preflight is safe.

## Deterministic Ordering

Source artifact records are sorted deterministically by artifact role. Review
artifact index entries use a fixed role order. JSON outputs are written with
sorted keys. Stable decision fields remain deterministic across equivalent
runs.

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
- No next bounded smoke iteration execution.
- No next iteration output directory creation.
- No production scan approval.
- No production promotion.
- No automatic approval.
- No autonomous execution.
- No candidate raw content read.
- No candidate file hashing by the review.
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

Required validation commands for this branch:

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

Final post-commit `make ci` result: passed.

Final `git diff --check` result: passed.

Final `git status --short` result: clean.

Final branch verification state: verified on
`feat/local-asset-bounded-smoke-cycle-human-review-v1` after syncing from
`main`.

## Next Recommended Branch

`feat/local-asset-next-bounded-smoke-iteration-admission-v1`
