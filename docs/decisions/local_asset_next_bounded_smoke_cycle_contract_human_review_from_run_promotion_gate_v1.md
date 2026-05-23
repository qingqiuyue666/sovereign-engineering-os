# Local Asset Next Bounded Smoke Cycle Contract Human Review From Run Promotion Gate v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch:
`feat/local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate-v1`

## Objective

Add a non-executing human review/admission artifact that consumes only a ready
next bounded smoke cycle contract generated from an approved next bounded
smoke iteration run promotion gate. The artifact records bounded admission
eligibility for a later separate execution-request/admission step.

This is still not production approval.

## Behavior Added

The branch adds
`build_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate(...)`,
the launcher
`run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_launcher(...)`,
the CLI command
`launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate`,
and task graph support for capability
`launch_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate`.

Required builder inputs are `cycle_contract_output_dir`, `output_dir`, and
`human_review_id`. Optional metadata is `project_id`, `reviewer_id`, and
`operator_notes`.

## CLI

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate \
  --cycle-contract-output-dir /path/to/next-cycle-contract-output \
  --output-dir /path/to/next-cycle-contract-human-review-output \
  --human-review-id next-cycle-contract-review-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

## Schema

The human review JSON uses `human_review_type:
local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_v1`,
`authority: non_authority_bounded_cycle_human_review_record`, and
`execution_capability:
local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_only`.

When ready, it emits `human_review_status =
next_bounded_smoke_cycle_contract_human_review_ready`,
`human_review_decision =
approve_next_bounded_smoke_cycle_contract_for_bounded_admission`, and
`next_allowed_action =
admit_next_bounded_smoke_cycle_contract_for_later_execution_request`.

It records inherited cycle contract, review packet, runner, request, limits,
candidate count, candidate byte, max-depth, and bounded file record metadata
only. Bounded file records remain metadata and must not contain raw content
fields.

## Source Artifact Policy

The human review reads only generated cycle contract artifacts by explicit
filename from `cycle_contract_output_dir`. It does not recursively index that
directory or candidate input files.

Required source artifacts:

- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional source artifacts:

- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist.md`

Malformed JSON, source artifact symlinks, type mismatches, missing required
source artifacts, and hash mismatches block. The source contract manifest
must hash-bind the contract and optional summary/checklist when present. The
source artifact index manifest must hash-bind the source artifact index.

## Required Artifacts

The output directory must already exist. It receives:

- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed on existing files or symlink
collisions at expected output paths.

## Readiness Rules

The human review is ready only when the source cycle contract reports:

- `contract_status = next_bounded_smoke_cycle_contract_ready`
- `contract_decision =
  create_bounded_smoke_cycle_contract_from_approved_run`
- `next_allowed_action =
  submit_next_bounded_smoke_cycle_contract_for_human_review`
- `cycle_contract_created=true`
- `cycle_contract_from_run_promotion_gate=true`
- `production_scan_approved=false`
- `production_promotion_granted=false`
- `automatic_approval_performed=false`
- `autonomous_execution_performed=false`
- `runner_execution_performed_by_contract=false`
- `review_packet_generation_performed_by_contract=false`
- `run_promotion_gate_reexecution_performed=false`
- `required_human_approval=true`
- `required_human_review=true`
- `contract_blockers`, `missing_required_artifacts`, and
  `untrusted_artifacts` are empty
- every required source boundary false flag is present, boolean, and false
- `deterministic_ordering=true`

## Bounded Admission Only

The ready human review sets `bounded_cycle_contract_human_review_created=true`
and `bounded_cycle_admission_allowed=true`. This permits only a later
separate bounded admission/execution-request step. It does not execute the
next cycle.

## Failure Behavior

If `output_dir` is missing, unsafe, overlapping with the source directory, or
already contains expected output files, the builder returns a structured
failure and writes no artifacts. If source artifacts are missing, malformed,
untrusted, not ready, or boundary-unsafe while `output_dir` is safe, it writes
a blocked human review artifact for review and repair.

## Explicit Non-Behavior

This branch does not create a production gate, run a production scan, grant
production promotion, execute a runner, regenerate a run review packet,
re-execute a run promotion gate, regenerate a cycle contract, read live
candidate files, list live candidate directories, hash live candidate input
files, validate live candidate paths, mutate upstream outputs, move/rename/
delete files, deduplicate files, copy raw private content, add media
organizer behavior, use network access, call model APIs, invoke external
runtimes, add UI, add Operator Console behavior, add watcher/daemon behavior,
grant automatic approval, or grant autonomous execution.
