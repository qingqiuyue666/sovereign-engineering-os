# Local Asset Bounded Smoke Cycle Contract v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`<repo-root>`

Branch: `feat/local-asset-bounded-smoke-cycle-contract-v1`

## Objective

Add a non-authoritative, replayable contract layer that binds the completed
local asset bounded smoke cycle:

readiness -> human-approved bounded smoke run -> smoke review packet -> smoke
promotion gate -> bounded smoke iteration -> iteration review packet ->
iteration promotion gate.

The new layer synthesizes generated artifacts only. It does not execute a
runtime stage or grant production authority.

## Changed Files

- `kernel/assets/local_asset_bounded_smoke_cycle_contract.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_bounded_smoke_cycle_contract.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_bounded_smoke_cycle_contract_v1.md`

## Behavior Added

The branch adds `build_local_asset_bounded_smoke_cycle_contract(...)` and the
CLI command `launch-local-asset-bounded-smoke-cycle-contract`. The builder
requires all seven upstream generated output roots plus a pre-existing output
directory. It writes:

- `local_asset_bounded_smoke_cycle_contract.json`
- `local_asset_bounded_smoke_cycle_contract_manifest.json`
- `local_asset_bounded_smoke_cycle_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive. Missing output directories, existing output files,
symlinked roots, and unsafe root overlaps fail closed without writing cycle
artifacts.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-bounded-smoke-cycle-contract \
  --readiness-output-dir /path/to/readiness-output \
  --smoke-output-dir /path/to/initial-smoke-output \
  --smoke-review-output-dir /path/to/smoke-review-output \
  --smoke-promotion-output-dir /path/to/smoke-promotion-output \
  --iteration-output-dir /path/to/iteration-output \
  --iteration-review-output-dir /path/to/iteration-review-output \
  --iteration-promotion-output-dir /path/to/iteration-promotion-output \
  --output-dir /path/to/cycle-contract-output \
  --project-id demo_project
```

## Schema

The contract JSON uses `contract_type:
local_asset_bounded_smoke_cycle_contract_v1`, `authority: non_authority`, and
`execution_capability: local_asset_bounded_smoke_cycle_contract_only`.

It records `project_id`, `output_dir`, chain roots, cycle status and decision,
the only next allowed action, actions allowed after human review, disallowed
actions, stage summaries, duplicate/quarantine/incremental/SQLite summaries,
blockers, source artifacts, missing required artifacts, untrusted artifacts,
deterministic ordering, explicit false boundary flags, and human review
requirements.

Status values:

- `cycle_contract_ready`
- `cycle_contract_ready_with_warnings`
- `blocked_missing_required_artifacts`
- `blocked_untrusted_artifacts`
- `blocked_incomplete_cycle`
- `blocked_quarantine`
- `blocked_duplicates`
- `blocked_incremental_changes`
- `blocked_production_boundary_violation`
- `blocked_unknown`

Decision values:

- `bind_completed_bounded_smoke_cycle`
- `bind_completed_cycle_with_human_warnings`
- `reject_and_repair_artifacts`
- `reject_and_repair_cycle`
- `inspect_quarantine`
- `inspect_duplicates`
- `inspect_incremental_changes`
- `reject_boundary_violation`

The only `next_allowed_action` is
`human_review_bounded_smoke_cycle_contract`.

## Source Artifact Policy

The contract reads only generated artifacts from the declared upstream output
roots. It may hash generated artifact files only. It does not scan candidate
directories, read candidate file contents, hash candidate input files, copy raw
private content, recursively index upstream output directories, or index
candidate inputs.

## Required Artifacts

Required source artifacts include readiness report/summary/index artifacts,
initial human smoke approval/admission/summary/index artifacts, initial scan
receipt/manifest/validation/quarantine/duplicate/index artifacts, smoke review
packet/index artifacts, smoke promotion decision/index artifacts, bounded
iteration result/signoff/admission/index artifacts, delegated iteration smoke
and scan artifacts, iteration review packet/index artifacts, and iteration
promotion decision/index artifacts.

Generated SQLite and incremental scan adjuncts are bound when present and are
not required when the upstream chain omits them.

## Readiness Rules

The cycle is ready only when all required artifacts exist and are trusted, the
readiness report is ready, initial smoke was admitted and completed, initial
scan completed, smoke review is `review_ready`, smoke promotion allows only
the next bounded smoke iteration, the bounded smoke iteration completed with
valid signoff, delegated iteration smoke and scan completed, iteration review
is `review_ready`, iteration promotion is an
`iteration_promotion_candidate`, the iteration promotion decision is
`allow_next_bounded_smoke_iteration`, and
`next_bounded_smoke_iteration_allowed` is true.

The ready state also requires no production flags, mutation flags, duplicate
deletion, quarantine, duplicate groups, suspicious incremental changes, or
blocking warnings.

## Blocker Logic

Missing required artifacts produce `blocked_missing_required_artifacts` and
`reject_and_repair_artifacts`.

Malformed, type-mismatched, symlinked, or hash-mismatched generated artifacts
produce `blocked_untrusted_artifacts` and `reject_and_repair_artifacts`.

Any production or mutation boundary violation produces
`blocked_production_boundary_violation` and `reject_boundary_violation`.

Any quarantine produces `blocked_quarantine` and `inspect_quarantine`. Any
duplicate group produces `blocked_duplicates` and `inspect_duplicates`. Any
suspicious or compare-previous incremental change produces
`blocked_incremental_changes` and `inspect_incremental_changes`.

Incomplete cycle stages produce `blocked_incomplete_cycle` and
`reject_and_repair_cycle`.

## Artifact Index Relationship

The cycle `artifact_index.json` binds only the four cycle-level artifacts:
contract, contract manifest, summary, and human review checklist. It does not
recursively index upstream output roots and does not index candidate input
files.

The cycle contract manifest records hashes for the contract, summary, human
review checklist, and source generated artifacts.

## Task Graph Relationship

The local asset task graph supports `adapter_id: local_asset_runtime` with
`capability: launch_local_asset_bounded_smoke_cycle_contract`. The node exposes
contract paths, status, decision, next allowed action, blocker count, human
review flags, and explicit false boundary flags.

`task_graph_artifact_outputs.py` binds the four cycle-level artifact roles:

- `local_asset_bounded_smoke_cycle_contract`
- `local_asset_bounded_smoke_cycle_contract_manifest`
- `local_asset_bounded_smoke_cycle_summary`
- `local_asset_bounded_smoke_cycle_human_review_checklist`

## Failure Behavior

The builder fails closed before writing artifacts when the output directory is
missing, any input root is missing or symlinked, an output file already exists,
or roots overlap unsafely. Missing or untrusted upstream generated artifacts
produce a blocked contract only after safe preflight succeeds.

## Deterministic Ordering

Source artifact records are sorted deterministically by root key and artifact
role. Blockers are sorted by blocker role. Artifact index entries use a fixed
role order. JSON outputs are written with sorted keys.

## Explicit Non-Behavior

- No scan execution.
- No readiness execution.
- No human smoke execution.
- No smoke review packet execution.
- No smoke promotion gate execution.
- No bounded smoke iteration execution.
- No iteration review packet execution.
- No iteration promotion gate execution.
- No production scan approval.
- No production promotion.
- No automatic approval.
- No autonomous execution.
- No candidate raw content read.
- No candidate file hashing by the contract.
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
`feat/local-asset-bounded-smoke-cycle-contract-v1` after syncing from `main`.

## Next Recommended Branch

`feat/local-asset-bounded-smoke-cycle-human-review-v1`
