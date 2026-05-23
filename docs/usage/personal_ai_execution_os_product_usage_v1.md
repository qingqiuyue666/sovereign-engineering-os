# Personal AI Execution OS Product Usage v1

All commands are local-first. They produce JSON on stdout and write a
human-readable summary into the requested output directory. Existing outputs
are not overwritten.

## Office Workflow

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-office-workflow \
  --input-workbook /path/to/input.xlsx \
  --output-dir /path/to/output
```

Performs readonly XLSX inspection and output planning only. Approved output
writing is a separate approval-gated workflow.

## Local Asset Scan

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-scan \
  --input-dir /path/to/assets \
  --output-dir /path/to/output \
  --previous-scan-output-dir /path/to/previous-output \
  --recursive \
  --project-id demo_project
```

Performs a read-only local asset scan. By default it does not scan nested
directories and excludes hidden files; use `--recursive` and `--include-hidden`
only when those paths should be included.

`--previous-scan-output-dir` is optional. When omitted, the launcher writes a
baseline incremental plan with `plan_mode = baseline_no_previous_scan`; all
current scanned assets are classified as `new`, with no missing, changed, or
unchanged assets. When provided, it must point to an existing non-symlink
previous scan output directory that is separate from the current `output_dir`;
the launcher writes `plan_mode = compare_previous_scan` and compares only
generated scan artifacts from the previous output directory.

The scan writes reports only to `output_dir` and fails closed if expected
output files already exist. It does not move, rename, delete, or reorganize
input files, and it is not a media organizer. It does not call model APIs, does
not call the network, and does not launch ComfyUI, Blender, Houdini, After
Effects, DaVinci, or a browser.

On success, the launcher also writes `launcher_summary.md`,
`asset_scan_run_receipt.json`, `local_asset_index.sqlite`,
`local_asset_sqlite_index_manifest.json`, and
`local_asset_sqlite_query_summary.md`. It then writes the incremental planning
artifacts `local_asset_incremental_scan_plan.json`,
`local_asset_incremental_scan_manifest.json`, and
`local_asset_incremental_scan_summary.md`, then binds the scan outputs into the
existing artifact index surface by emitting `artifact_index.json` and
`artifact_index_manifest.json`. The receipt records the completed scan counts,
quarantine count, retry/replay hint, and explicit no-scope-expansion
boundaries.

The SQLite index is a per-scan output artifact only. It stays inside that
scan's `output_dir`, is a metadata/query index over generated scan artifacts,
does not copy raw private asset content, and does not attach to the global OS
engine database. It does not add UI, desktop app behavior, Operator Console
behavior, external runtime activation, or production autonomy.

The incremental scan plan is also non-authoritative and review-only. It does
not execute a cache, does not automatically skip hashing or scanning, does not
mutate inputs, does not move, rename, delete, deduplicate, or organize media
files, does not write to a global database, does not add UI or Operator
Console behavior, does not run real-folder smoke, does not activate external
runtimes, and does not add production autonomy.

On safe failure cases where `output_dir` already exists and is safe to write
into, the launcher writes `asset_scan_failure_bundle.json` and
`asset_scan_failure_summary.md`. If `output_dir` is missing, the launcher does
not create it and returns a structured failure payload without writing a
failure bundle.

## Local Asset Smoke Readiness

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-readiness \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/output \
  --recursive \
  --include-hidden \
  --project-id demo_project
```

Required arguments are `--candidate-input-dir` and `--output-dir`. Optional
arguments are `--recursive`, `--include-hidden`, `--project-id`,
`--max-entries`, `--max-depth`, and `--max-total-bytes`.

This command performs metadata-only readiness inspection before any future
human-approved real-folder smoke run. It inspects path names, path type,
directory structure, file sizes from filesystem metadata, extensions, hidden
path status, symlink status, unsafe directory names, and secret-looking path
names. It does not run a real asset scan, does not hash raw candidate files,
does not read raw candidate file contents, does not copy private content, and
does not mutate, move, rename, or delete input files.

The default safety limits are:

- `--max-entries 50000`
- `--max-depth 20`
- `--max-total-bytes 500000000000`

`output_dir` must already exist, must not be a symlink, and must not overlap
with `candidate_input_dir` in either direction. The candidate input directory
must exist, be a directory, and not be a symlink. If a limit is exceeded, the
command writes readiness artifacts with
`readiness_status = blocked_limit_exceeded` and exits successfully because the
readiness harness safely blocked the future smoke.

The command writes:

- `local_asset_smoke_readiness_report.json`
- `local_asset_smoke_readiness_manifest.json`
- `local_asset_smoke_readiness_summary.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are inside `output_dir` and fail closed if any expected output
already exists. The artifact index remains metadata-only and
non-authoritative.

Readiness statuses are:

- `ready`
- `ready_with_warnings`
- `blocked_safety_risk`
- `blocked_limit_exceeded`
- `failed_preflight`

Readiness decisions are `allow_human_review_for_future_smoke` or
`block_future_smoke_until_review`. Human approval is required before any
future real-folder smoke. This command does not enable real-folder smoke by
itself and does not add UI, Operator Console behavior, watcher/daemon behavior,
network access, model API calls, external runtime activation, global database
state, or production autonomy.

## Local Asset Human-Approved Smoke Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-human-smoke-run \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/human-smoke-output-root \
  --readiness-report /path/to/readiness/local_asset_smoke_readiness_report.json \
  --human-approval-id reviewer-ticket-123 \
  --human-approval-phrase I_APPROVE_LOCAL_ASSET_SMOKE_RUN \
  --recursive \
  --project-id demo_project \
  --max-smoke-files 25 \
  --max-smoke-bytes 100000000 \
  --max-smoke-depth 4
```

Required arguments are `--candidate-input-dir`, `--output-dir`,
`--readiness-report`, `--human-approval-id`, and
`--human-approval-phrase`. The approval phrase must match exactly:
`I_APPROVE_LOCAL_ASSET_SMOKE_RUN`. The phrase plaintext is never persisted;
only its SHA-256 hash is written to the approval artifact.

Optional arguments are `--recursive`, `--include-hidden`, `--project-id`,
`--max-smoke-files`, `--max-smoke-bytes`, `--max-smoke-depth`, and
`--previous-scan-output-dir`. Default smoke limits are:

- `--max-smoke-files 100`
- `--max-smoke-bytes 2000000000`
- `--max-smoke-depth 8`

The command consumes a previous
`local_asset_smoke_readiness_report.json`. The readiness report must come from
the metadata-only readiness harness, must require human approval, must have
`readiness_decision = allow_human_review_for_future_smoke`, and must have
`readiness_status = ready` or `ready_with_warnings`. It rejects
`blocked_safety_risk`, `blocked_limit_exceeded`, and `failed_preflight`.

The smoke run root `output_dir` must already exist and must not be a symlink.
The candidate input directory and readiness report must exist and must not be
symlinks. Candidate path, `recursive`, and `include_hidden` must match the
readiness report; `project_id` must match when both are present. The smoke
root and candidate directory must not overlap in either direction.

This command uses a subdirectory layout:

- `output_dir/control/local_asset_human_smoke_approval.json`
- `output_dir/control/local_asset_human_smoke_admission_receipt.json`
- `output_dir/local_asset_human_smoke_run_summary.md`
- `output_dir/scan/` for the normal `launch-local-asset-scan` output stack
- `output_dir/artifact_index.json`
- `output_dir/artifact_index_manifest.json`

Before invoking the existing scan launcher, it performs a metadata-only
bounded precheck and fails closed if the candidate would exceed
`max_smoke_files`, `max_smoke_bytes`, or `max_smoke_depth`. It also rejects
smoke limits that exceed the corresponding readiness report limits where
available. It does not silently truncate, sample, or partially scan.

The actual scan is delegated to the existing local asset scan launcher using
the deterministic `output_dir/scan/` subdirectory. The scan remains read-only
and writes the normal scan artifacts there, including `asset_manifest.json`,
`asset_index.json`, `duplicates_report.json`, `media_inventory.md`,
`asset_runtime_audit_log.jsonl`, validation and quarantine reports,
`launcher_summary.md`, `asset_scan_run_receipt.json`,
`local_asset_index.sqlite`, SQLite query/index manifests, incremental scan
plan artifacts, and the scan-level `artifact_index.json` and
`artifact_index_manifest.json`.

The root artifact index is an explicit control-and-scan reference index. It
does not recursively crawl private assets, does not copy raw content, and
includes the approval, admission, smoke summary, scan artifact index, scan
artifact index manifest, and key scan output paths when present.

This is human-approved bounded smoke only. It does not add automatic approval,
production scanning, watcher/daemon behavior, UI, desktop app behavior,
Operator Console behavior, global database state, input mutation, file
movement, file renaming, file deletion, duplicate deletion, media organizer
behavior, network access, model API calls, external runtime activation,
browser runtime activation, ComfyUI/Blender/Houdini/After Effects/DaVinci
activation, HFX changes, or production autonomy.

## Local Asset Smoke Review Packet

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-review-packet \
  --smoke-output-dir /path/to/human-smoke-output-root \
  --output-dir /path/to/review-packet-output \
  --project-id demo_project
```

Required arguments are `--smoke-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The review `output_dir` is not created
automatically. It must not equal `smoke_output_dir`, must not be inside it,
and must not contain it. If the generated admission receipt safely exposes a
`candidate_input_dir`, the review `output_dir` must also not be inside that
candidate input directory.

This command consumes generated human-approved smoke-run artifacts only. It
reads the smoke root control artifacts, smoke summary, root artifact index,
scan artifact index, scan reports, generated SQLite manifest/query summary,
incremental plan artifacts, and generated failure artifacts when present. It
may hash generated artifact files. It does not run a scan, does not re-run
readiness, does not hash candidate files, does not read raw candidate file
contents, does not copy raw private content, does not mutate inputs, and does
not mutate the smoke output root.

The command writes these review artifacts into `output_dir`:

- `local_asset_smoke_review_packet.json`
- `local_asset_smoke_review_packet_manifest.json`
- `local_asset_smoke_review_summary.md`
- `local_asset_smoke_human_decision_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
The review packet summarizes approval, admission, readiness, scan counts,
duplicate groups, quarantine counts and top reasons, generated SQLite manifest
row counts, incremental plan counts, failure state, warning state, and the
explicit no-scope-expansion boundaries.

Review packet statuses are:

- `review_ready`
- `review_ready_with_warnings`
- `review_blocked_missing_required_artifacts`
- `review_blocked_failed_smoke_run`
- `review_blocked_untrusted_artifacts`

Recommended human decisions are:

- `approve_next_bounded_smoke_iteration`
- `inspect_quarantine_before_next_run`
- `inspect_duplicates_before_next_run`
- `inspect_incremental_changes_before_next_run`
- `reject_and_repair_smoke_run`

The checklist is for human review only. It does not suggest deleting, moving,
renaming, or deduplicating files, does not grant automatic approval, does not
enable production scanning, does not add UI, desktop app behavior, Operator
Console behavior, watcher/daemon behavior, network access, model API calls,
external creative runtime activation, HFX changes, global database state, or
production autonomy.

## Local Asset Smoke Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-promotion-gate \
  --review-output-dir /path/to/review-packet-output \
  --output-dir /path/to/promotion-gate-output \
  --project-id demo_project
```

Required arguments are `--review-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The promotion `output_dir` is not
created automatically. It must not equal `review_output_dir`, must not be
inside it, and must not contain it. If the generated review packet safely
exposes a `smoke_output_dir` or `candidate_input_dir`, the promotion
`output_dir` must not be inside either upstream directory.

This command consumes generated review packet artifacts only:

- `local_asset_smoke_review_packet.json`
- `local_asset_smoke_review_packet_manifest.json`
- `local_asset_smoke_review_summary.md` when present
- `local_asset_smoke_human_decision_checklist.md` when present
- `artifact_index.json`
- `artifact_index_manifest.json`

It may hash those generated review artifacts. It does not scan, run
readiness, run human smoke, hash candidate files, read raw candidate file
contents, copy raw private content, mutate review packet outputs, mutate smoke
outputs, mutate inputs, move files, rename files, delete files, delete
duplicates, perform media organizer behavior, use network access, call model
APIs, invoke external runtimes, or approve production use.

The command writes these promotion gate artifacts into `output_dir`:

- `local_asset_smoke_promotion_decision.json`
- `local_asset_smoke_promotion_gate_manifest.json`
- `local_asset_smoke_promotion_summary.md`
- `local_asset_smoke_promotion_human_signoff_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
If required review artifacts are missing and the promotion output directory is
safe, the gate writes a blocked decision rather than pretending promotion is
allowed.

Promotion gate status values are:

- `promotion_candidate`
- `blocked_missing_review_artifacts`
- `blocked_untrusted_review_packet`
- `blocked_failed_smoke_run`
- `blocked_quarantine`
- `blocked_duplicates`
- `blocked_incremental_changes`
- `blocked_warnings`
- `blocked_unknown`

Promotion decision values are:

- `allow_next_bounded_smoke_iteration`
- `block_until_human_inspects_quarantine`
- `block_until_human_inspects_duplicates`
- `block_until_human_inspects_incremental_changes`
- `block_until_smoke_run_repaired`
- `block_until_review_packet_repaired`

The gate only allows the next bounded smoke iteration when the review packet
is clean: `review_packet_status=review_ready`, recommended decision is
`approve_next_bounded_smoke_iteration`, smoke and scan are complete,
production scan is false, input mutation is false, duplicate deletion is
false, quarantine count is zero, duplicate group count is zero, suspicious
incremental changes are zero, and no blocking warnings are present. It never
grants production promotion and never approves production scanning.

## Local Asset Bounded Smoke Iteration

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-bounded-smoke-iteration \
  --promotion-output-dir /path/to/promotion-gate-output \
  --candidate-input-dir /path/to/candidate-assets \
  --readiness-report /path/to/readiness/local_asset_smoke_readiness_report.json \
  --output-dir /path/to/iteration-output \
  --human-signoff-id reviewer-ticket-456 \
  --human-signoff-phrase I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION \
  --recursive \
  --project-id demo_project \
  --max-smoke-files 100 \
  --max-smoke-bytes 1073741824 \
  --max-smoke-depth 12
```

Required arguments are `--promotion-output-dir`, `--candidate-input-dir`,
`--readiness-report`, `--output-dir`, `--human-signoff-id`, and
`--human-signoff-phrase`. The required signoff phrase is exactly
`I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION`; the provided phrase plaintext is not
persisted. Optional arguments are `--project-id`,
`--previous-scan-output-dir`, `--recursive`, `--include-hidden`,
`--max-smoke-files`, `--max-smoke-bytes`, and `--max-smoke-depth`.

Default bounded iteration limits are:

- `--max-smoke-files 100`
- `--max-smoke-bytes 1073741824`
- `--max-smoke-depth 12`

The command consumes generated promotion gate artifacts only:

- `local_asset_smoke_promotion_decision.json`
- `local_asset_smoke_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

It admits the next bounded smoke iteration only when the promotion decision is
`promotion_gate_status=promotion_candidate`,
`promotion_decision=allow_next_bounded_smoke_iteration`,
`next_bounded_smoke_iteration_allowed=true`,
`production_promotion_granted=false`, `production_scan_approved=false`, and
the review recommendation was `approve_next_bounded_smoke_iteration` with no
promotion blockers. It also verifies promotion manifest hashes and the
promotion artifact index manifest hash.

`output_dir` must already exist, must be a real directory, must not be a
symlink, and is never created automatically. It must not equal or overlap
`promotion_output_dir` or `candidate_input_dir` in either direction, and must
not be inside the review, smoke, or previous candidate directories when those
paths are discoverable from the promotion decision.

On valid promotion gate review and valid explicit human signoff, this command
creates only `output_dir/control/` and `output_dir/smoke/`, then delegates to
the existing `launch-local-asset-human-smoke-run` controls in the `smoke/`
subdirectory. The delegated smoke run still requires readiness, uses the
existing human-approved smoke launcher path, preserves bounded max files,
bytes, and depth, and writes the normal human smoke output stack under
`output_dir/smoke/`.

The iteration writes:

- `control/local_asset_bounded_smoke_iteration_signoff.json`
- `control/local_asset_bounded_smoke_iteration_admission.json`
- `local_asset_bounded_smoke_iteration_result.json`
- `local_asset_bounded_smoke_iteration_manifest.json`
- `local_asset_bounded_smoke_iteration_summary.md`
- `local_asset_bounded_smoke_iteration_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`
- `smoke/` delegated human smoke outputs when admitted

All writes are exclusive and fail closed if expected iteration outputs already
exist. If the promotion gate is blocked or the signoff phrase is invalid, the
command writes blocked iteration artifacts when the output directory is safe,
does not create `smoke/`, and does not invoke the smoke launcher.

This command only enables another bounded smoke iteration after promotion-gate
review and explicit human signoff. It does not approve production scan, does
not grant production promotion, does not add automatic approval, does not add
watcher/daemon behavior, does not add UI or Operator Console behavior, does
not mutate inputs or upstream outputs, does not move, rename, delete, or
deduplicate files, does not perform media organizer behavior, does not use
network access, does not call model APIs, and does not invoke external
creative runtimes.

## Local Asset Smoke Iteration Review Packet

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-iteration-review-packet \
  --iteration-output-dir /path/to/iteration-output \
  --output-dir /path/to/iteration-review-output \
  --project-id demo_project
```

Required arguments are `--iteration-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The review `output_dir` is not created
automatically. It must not equal `iteration_output_dir`, must not be inside
it, and must not contain it. If generated iteration artifacts safely expose
the candidate input directory, promotion output directory, or delegated smoke
output directory, the review `output_dir` must not be inside any of them.

This command consumes generated bounded smoke iteration artifacts only,
including the iteration result, manifest, root artifact index, signoff,
admission, delegated smoke artifacts under `smoke/`, and delegated scan
artifacts under `smoke/scan/`. It may hash generated artifact files. It does
not run a scan, run readiness, run human smoke, run bounded smoke iteration,
run promotion gate, hash candidate files, read raw candidate file contents,
copy raw private content, mutate inputs, mutate iteration outputs, mutate
smoke outputs, approve production scanning, or grant production promotion.

The command writes these review artifacts into `output_dir`:

- `local_asset_smoke_iteration_review_packet.json`
- `local_asset_smoke_iteration_review_packet_manifest.json`
- `local_asset_smoke_iteration_review_summary.md`
- `local_asset_smoke_iteration_human_decision_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
The review packet summarizes outer iteration signoff, admission, promotion
gate validation, delegated human smoke state, delegated scan state,
quarantine, duplicates, generated SQLite manifest/query summary, incremental
plan counts, failure state, warning state, and explicit boundaries.

Iteration review status values are:

- `review_ready`
- `review_ready_with_warnings`
- `review_blocked_missing_required_artifacts`
- `review_blocked_failed_iteration`
- `review_blocked_untrusted_artifacts`

Recommended human decision values are:

- `generate_promotion_gate_for_iteration`
- `inspect_iteration_quarantine_before_promotion`
- `inspect_iteration_duplicates_before_promotion`
- `inspect_iteration_incremental_changes_before_promotion`
- `reject_and_repair_iteration`

A clean review can recommend generating a promotion gate for the iteration.
It never recommends production scan. The checklist is for human review only:
it does not suggest deleting, moving, renaming, or deduplicating files, does
not grant automatic approval, and does not add UI, desktop app behavior,
Operator Console behavior, watcher/daemon behavior, network access, model API
calls, external creative runtime activation, HFX changes, global database
state, or production autonomy.

## Local Asset Iteration Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-iteration-promotion-gate \
  --iteration-review-output-dir /path/to/iteration-review-output \
  --output-dir /path/to/iteration-promotion-output \
  --project-id demo_project
```

Required arguments are `--iteration-review-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The promotion `output_dir` is not
created automatically. It must not equal the iteration review output
directory, must not be inside it, and must not contain it. If generated
iteration review artifacts safely expose the iteration output directory,
candidate input directory, delegated smoke output directory, or prior smoke
promotion output directory, the promotion `output_dir` must not be inside any
of them.

This command consumes generated smoke iteration review packet artifacts only:

- `local_asset_smoke_iteration_review_packet.json`
- `local_asset_smoke_iteration_review_packet_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

It may also read the generated optional iteration review summary and human
decision checklist. It may hash generated iteration review packet artifacts.
It does not run a scan, run readiness, run human smoke, run bounded smoke
iteration, run smoke promotion gate, run iteration review packet generation,
hash candidate files, read raw candidate file contents, copy raw private
content, mutate inputs, mutate iteration review outputs, mutate iteration
outputs, mutate delegated smoke outputs, approve production scanning, grant
production promotion, or recommend production scan.

The command writes these promotion artifacts into `output_dir`:

- `local_asset_iteration_promotion_decision.json`
- `local_asset_iteration_promotion_gate_manifest.json`
- `local_asset_iteration_promotion_summary.md`
- `local_asset_iteration_promotion_human_signoff_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Iteration promotion gate status values are:

- `iteration_promotion_candidate`
- `blocked_missing_iteration_review_artifacts`
- `blocked_untrusted_iteration_review_packet`
- `blocked_failed_iteration`
- `blocked_quarantine`
- `blocked_duplicates`
- `blocked_incremental_changes`
- `blocked_warnings`
- `blocked_unknown`

Iteration promotion decision values are:

- `allow_next_bounded_smoke_iteration`
- `block_until_human_inspects_iteration_quarantine`
- `block_until_human_inspects_iteration_duplicates`
- `block_until_human_inspects_iteration_incremental_changes`
- `block_until_iteration_repaired`
- `block_until_iteration_review_packet_repaired`

The gate only allows the next bounded smoke iteration when the iteration
review packet is trusted, its manifest and artifact index manifest hashes
match, the review status is `review_ready`, the recommended decision is
`generate_promotion_gate_for_iteration`, the iteration is complete, bounded
smoke iteration was performed, smoke and scan completion are true, production
promotion and production scan flags are false, input mutation and duplicate
deletion are false, quarantine count is zero, duplicate group count is zero,
suspicious incremental changes count is zero, and no blocking warning is
present. The decision is non-authoritative and always requires human signoff.

## Local Asset Bounded Smoke Cycle Contract

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

All seven input directories and `--output-dir` are required. They must already
exist, must be real directories, and must not be symlinks. The cycle contract
output directory is not created automatically. It must be separate from every
input root, must not be inside an input root, must not contain an input root,
and input roots must not overlap each other.

The command consumes generated artifacts from the completed readiness, human
smoke, smoke review, smoke promotion, bounded smoke iteration, iteration
review, and iteration promotion chain. It binds generated reports, decisions,
manifests, artifact indexes, scan receipts, duplicate/quarantine reports, and
optional generated SQLite/incremental adjuncts when present. It may hash those
generated artifacts only. It does not recursively index upstream directories
and does not read or hash candidate input files.

The command writes:

- `local_asset_bounded_smoke_cycle_contract.json`
- `local_asset_bounded_smoke_cycle_contract_manifest.json`
- `local_asset_bounded_smoke_cycle_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Cycle contract status values are:

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

Cycle contract decision values are:

- `bind_completed_bounded_smoke_cycle`
- `bind_completed_cycle_with_human_warnings`
- `reject_and_repair_artifacts`
- `reject_and_repair_cycle`
- `inspect_quarantine`
- `inspect_duplicates`
- `inspect_incremental_changes`
- `reject_boundary_violation`

The only next allowed action emitted by the contract is
`human_review_bounded_smoke_cycle_contract`. After human review, the contract
allows only `next_bounded_smoke_iteration`, `stop_cycle`, `repair_artifacts`,
or `repair_cycle`. It disallows production scan, production promotion,
automatic approval, autonomous execution, candidate file mutation, duplicate
deletion, and media organizer behavior.

This command does not run scan, readiness, human smoke, smoke review packet
generation, smoke promotion gate, bounded smoke iteration, iteration review
packet generation, or iteration promotion gate. It does not approve production
scan, grant production promotion, copy raw private content, mutate upstream
outputs, mutate candidate input, move, rename, delete, or deduplicate files,
add UI or Operator Console behavior, start watcher/daemon behavior, use
network access, call model APIs, invoke external runtimes, or modify HFX.
Human review and human approval remain required.

## Local Asset Bounded Smoke Cycle Human Review

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

`--cycle-contract-output-dir` and `--output-dir` must already exist, must be
real directories, and must not be symlinks. The review output directory is not
created automatically. It must be separate from the cycle contract output
directory, must not be inside it, and must not contain it.

The required human signoff phrase is:
`I_REVIEWED_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT`. The phrase is validated
exactly, but only its SHA-256 hash is stored. The plaintext phrase is never
persisted in the decision, manifest, summary, checklist, or artifact index.

Allowed human decisions are:

- `approve_cycle_contract_for_next_bounded_smoke_iteration`
- `stop_cycle`
- `repair_artifacts`
- `repair_cycle`
- `inspect_quarantine`
- `inspect_duplicates`
- `inspect_incremental_changes`
- `reject_boundary_violation`

The command reads and binds only generated cycle contract artifacts:

- `local_asset_bounded_smoke_cycle_contract.json`
- `local_asset_bounded_smoke_cycle_contract_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional cycle summary and human review checklist markdown files when present

It does not recursively index the cycle contract output directory, upstream
output directories, or candidate input files. It does not read raw private
content or hash candidate input files.

The command writes:

- `local_asset_bounded_smoke_cycle_human_review_decision.json`
- `local_asset_bounded_smoke_cycle_human_review_manifest.json`
- `local_asset_bounded_smoke_cycle_human_review_summary.md`
- `local_asset_bounded_smoke_cycle_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Human review status values include:

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

The approval path is prepare-only. A valid approval over a trusted
`cycle_contract_ready` contract emits
`next_allowed_action: prepare_next_bounded_smoke_iteration_admission` and
`next_bounded_smoke_iteration_prepare_allowed: true`, while
`next_bounded_smoke_iteration_execute_allowed` remains false. This command
never executes the next bounded smoke iteration and never creates a next
iteration output directory.

This command does not run scan, readiness, human smoke, smoke review packet
generation, smoke promotion gate, bounded smoke iteration, iteration review
packet generation, iteration promotion gate, or cycle contract generation. It
does not approve production scan, grant production promotion, add automatic
approval or autonomy, mutate upstream outputs, mutate candidate inputs, move,
rename, delete, or deduplicate files, add media organizer behavior, add UI or
Operator Console behavior, start watcher/daemon behavior, use network access,
call model APIs, invoke external runtimes, or modify HFX.

## Local Asset Next Bounded Smoke Iteration Admission

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-admission \
  --cycle-human-review-output-dir /path/to/cycle-human-review-output \
  --output-dir /path/to/next-admission-output \
  --project-id demo_project \
  --requested-next-iteration-id iteration-002 \
  --operator-notes "optional notes"
```

`--cycle-human-review-output-dir` and `--output-dir` must already exist, must
be real directories, and must not be symlinks. The admission output directory
is not created automatically. It must be separate from the cycle human review
output directory, must not be inside it, and must not contain it.

This command consumes the already-recorded bounded smoke cycle human review
decision. It accepts no human signoff phrase and handles no plaintext approval
phrase. `--requested-next-iteration-id` is optional metadata only, and
`--operator-notes` is stored only when supplied.

The command reads and binds only generated cycle human review artifacts:

- `local_asset_bounded_smoke_cycle_human_review_decision.json`
- `local_asset_bounded_smoke_cycle_human_review_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional human review summary and checklist markdown files when present

It does not recursively index the cycle human review output directory, the
cycle contract output directory, upstream output directories, or candidate
input files. It does not read raw private content or hash candidate input
files.

The command writes:

- `local_asset_next_bounded_smoke_iteration_admission.json`
- `local_asset_next_bounded_smoke_iteration_admission_manifest.json`
- `local_asset_next_bounded_smoke_iteration_admission_summary.md`
- `local_asset_next_bounded_smoke_iteration_admission_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Admission is ready only when the generated human review decision, human review
manifest, human review artifact index, and artifact index manifest exist and
are trusted; manifest hashes match; the human review status is
`human_review_approved_next_bounded_smoke_iteration`; the human review decision
is `allow_prepare_next_bounded_smoke_iteration`; the human decision is
`approve_cycle_contract_for_next_bounded_smoke_iteration`; the signoff phrase
was not persisted; prepare is allowed; execute remains denied; the human
review next action is `prepare_next_bounded_smoke_iteration_admission`; the
cycle contract status and decision are ready/bind-only values; and production,
mutation, automatic approval, autonomous execution, and next-iteration
execution remain disallowed.

When ready, the admission record emits
`admission_status: next_bounded_smoke_iteration_admission_ready`,
`admission_decision: admit_prepare_next_bounded_smoke_iteration`, and
`next_allowed_action: create_next_bounded_smoke_iteration_execution_request`.
This admits only creation of a future execution request. It never executes the
next bounded smoke iteration, never creates a next iteration output directory,
never approves production scanning, and never grants production promotion.

## Local Asset Next Bounded Smoke Iteration Execution Request

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-execution-request \
  --next-admission-output-dir /path/to/next-admission-output \
  --output-dir /path/to/execution-request-output \
  --requested-next-iteration-id iteration-002 \
  --requested-candidate-input-dir /path/to/future-candidate-input \
  --requested-next-iteration-output-dir /path/to/future-iteration-output \
  --requested-max-files 25 \
  --requested-max-total-bytes 104857600 \
  --requested-max-depth 4 \
  --project-id demo_project \
  --request-id request-002 \
  --operator-id operator-001 \
  --operator-notes "optional notes" \
  --requested-compare-previous-scan-manifest-path /path/to/previous/asset_manifest.json \
  --requested-previous-iteration-artifact-index-path /path/to/previous/artifact_index.json
```

`--next-admission-output-dir` and `--output-dir` must already exist, must be
real directories, and must not be symlinks. The execution request output
directory is not created automatically. It must be separate from the next
admission output directory, must not be inside it, and must not contain it.
All request output writes are exclusive and fail closed on existing files.

The requested candidate input path, requested next iteration output path,
optional previous scan manifest path, and optional previous iteration artifact
index path are metadata only. This command does not create those paths, check
whether they exist, resolve them strictly, list candidate directories, read
candidate file contents, hash candidate input files, or validate candidate
content.

The command reads and binds only generated next admission artifacts:

- `local_asset_next_bounded_smoke_iteration_admission.json`
- `local_asset_next_bounded_smoke_iteration_admission_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional next admission summary and checklist markdown files when present

It does not recursively index the next admission output directory, cycle
human review output directory, cycle contract output directory, upstream
output directories, or candidate input files.

The command writes:

- `local_asset_next_bounded_smoke_iteration_execution_request.json`
- `local_asset_next_bounded_smoke_iteration_execution_request_manifest.json`
- `local_asset_next_bounded_smoke_iteration_execution_request_summary.md`
- `local_asset_next_bounded_smoke_iteration_execution_request_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

The execution request is ready only when the generated next admission JSON,
manifest, artifact index, and artifact index manifest exist and are trusted;
manifest hashes match; admission status is
`next_bounded_smoke_iteration_admission_ready`; admission decision is
`admit_prepare_next_bounded_smoke_iteration`; admission next action is
`create_next_bounded_smoke_iteration_execution_request`; prepare is admitted;
source execute permission is false; source next iteration execution and output
creation are false; production scan, production promotion, automatic
approval, and autonomous execution flags are false; requested metadata is
present; and requested limits are within bounds.

When ready, the request record emits
`request_status: next_bounded_smoke_iteration_execution_request_ready`,
`request_decision: create_future_bounded_smoke_iteration_execution_request`,
and `next_allowed_action: await_separate_bounded_smoke_iteration_runner`.
It creates only a durable request artifact for a later separate bounded smoke
iteration runner.

This command does not run scan, readiness, human smoke, review packet
generation, promotion gates, bounded smoke iteration, iteration review,
iteration promotion, cycle contract generation, cycle human review generation,
or next admission generation. It does not execute the next bounded smoke
iteration, create a next iteration output directory, create the requested next
iteration output directory, approve production scan, grant production
promotion, add automatic approval or autonomy, mutate upstream outputs, mutate
candidate input, move, rename, delete, or deduplicate files, add media
organizer behavior, add UI or Operator Console behavior, start watcher/daemon
behavior, use network access, call model APIs, invoke external runtimes, or
modify HFX.

Blocked statuses repair artifacts, repair human review, or reject boundary
violations. Missing required artifacts and untrusted artifacts repair
artifacts. Non-approved human review records and prepare denial repair human
review. Existing execute permission, production flags, mutation flags, malformed
records, or missing disallowed production/autonomy actions reject or repair
according to the recorded blocker.

This command does not run scan, readiness, human smoke, smoke review packet
generation, smoke promotion gate, bounded smoke iteration, iteration review
packet generation, iteration promotion gate, cycle contract generation, or
cycle human review generation. It does not approve production scan, grant
production promotion, add automatic approval or autonomy, mutate upstream
outputs, mutate candidate inputs, move, rename, delete, or deduplicate files,
add media organizer behavior, add UI or Operator Console behavior, start
watcher/daemon behavior, use network access, call model APIs, invoke external
runtimes, or modify HFX.

## Local Asset Next Bounded Smoke Iteration Runner Admission

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

`--execution-request-output-dir` and `--output-dir` must already exist, must
be real directories, and must not be symlinks. The runner admission output
directory is not created automatically. It must be separate from the execution
request output directory, must not be inside it, and must not contain it. All
runner admission output writes are exclusive and fail closed on existing files.

The required acknowledgement phrase is
`I_ACKNOWLEDGE_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ONLY`. The command
validates that phrase exactly and stores only its SHA-256 hash. The plaintext
acknowledgement phrase is never persisted in the runner admission artifact,
manifest, summary, checklist, or artifact index. Invalid acknowledgement writes
a blocked runner admission artifact when the output directory is safe.

The command reads and binds only generated execution request artifacts:

- `local_asset_next_bounded_smoke_iteration_execution_request.json`
- `local_asset_next_bounded_smoke_iteration_execution_request_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional execution request summary and checklist markdown files when present

It does not recursively index the execution request output directory, next
admission output directory, cycle human review output directory, cycle
contract output directory, upstream output directories, or candidate input
files. Requested candidate input path, requested next iteration output path,
previous scan manifest path, and previous iteration artifact index path are
copied only as inherited metadata from the trusted execution request artifact.
They are not created, resolved strictly, statted, listed, read, hashed, or
path-validated.

The command writes:

- `local_asset_next_bounded_smoke_iteration_runner_admission.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_summary.md`
- `local_asset_next_bounded_smoke_iteration_runner_admission_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Runner admission is ready only when the generated execution request JSON,
manifest, artifact index, and artifact index manifest exist and are trusted;
manifest hashes match; request status is
`next_bounded_smoke_iteration_execution_request_ready`; request decision is
`create_future_bounded_smoke_iteration_execution_request`; request next action
is `await_separate_bounded_smoke_iteration_runner`; the future execution
request was created; source execute permission, next iteration execution,
future output creation, requested future output creation, candidate
validation/list/read/hash flags, production approval, production promotion,
automatic approval, and autonomous execution are all false; runner admission
metadata is non-empty; admitted limits are valid; and admitted limits do not
exceed the requested execution request limits.

When ready, the runner admission record emits
`admission_status: next_bounded_smoke_iteration_runner_admission_ready`,
`admission_decision: admit_runner_to_consume_future_execution_request`, and
`next_allowed_action: await_separate_bounded_smoke_iteration_runner_execution`.
This admits only that a later separate bounded smoke iteration runner branch
may consume the request. It sets `runner_execution_allowed: false` and
`next_bounded_smoke_iteration_execute_allowed: false`.

This command is runner-admission-only. It does not run scan, readiness, human
smoke, smoke review packet generation, smoke promotion gate, bounded smoke
iteration, iteration review packet generation, iteration promotion gate, cycle
contract generation, cycle human review generation, next admission generation,
or execution request generation. It does not execute the runner, execute the
next bounded smoke iteration, create a next iteration output directory,
validate/stat/list candidate paths, read raw candidate content, hash candidate
input files, mutate upstream outputs, mutate candidate input, move, rename,
delete, or deduplicate files, add media organizer behavior, approve production
scan, grant production promotion, add automatic approval or autonomous
execution, add UI or Operator Console behavior, start watcher/daemon behavior,
use network access, call model APIs, invoke external runtimes, or modify HFX.

## Local Asset Next Bounded Smoke Iteration Runner

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

`--runner-output-dir` and `--actual-next-iteration-output-dir` must already
exist, must be real directories, and must not be symlinks. The runner does not
create the actual next iteration output directory and does not create the
candidate input directory. The actual output directory must textually match
the `requested_next_iteration_output_dir` inherited from the trusted runner
admission artifact after non-strict normalization. Runner output, runner
admission output, and actual iteration output directories must be separate and
non-overlapping. All writes are exclusive and fail closed on existing files.

The required execution acknowledgement phrase is
`I_EXECUTE_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_UNDER_ADMITTED_LIMITS`.
The runner validates the phrase exactly, stores only its SHA-256 hash, and
never persists the plaintext phrase in runner artifacts. Invalid
acknowledgement writes a blocked runner artifact when the runner output
directory is safe and does not write actual iteration artifacts.

The runner reads and binds only generated runner admission artifacts:

- `local_asset_next_bounded_smoke_iteration_runner_admission.json`
- `local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`
- optional runner admission summary and checklist markdown files when present

It verifies generated artifact type fields and manifest hashes. It does not
recursively index runner admission, execution request, next admission, cycle
human review, cycle contract, upstream output, actual iteration output, or
candidate input directories.

Runner execution is ready only after source runner admission trust succeeds;
runner admission status is
`next_bounded_smoke_iteration_runner_admission_ready`; runner admission
decision is `admit_runner_to_consume_future_execution_request`; next allowed
action is `await_separate_bounded_smoke_iteration_runner_execution`;
`runner_consume_request_admitted` is true; source execution, source iteration
execution, output creation, candidate access, production approval, production
promotion, automatic approval, and autonomy flags are false; runner execution
metadata is non-empty; the acknowledgement phrase is valid; admitted limits are
valid; and the actual output directory matches the requested output directory.

Only after those trust and acknowledgement gates pass does the runner validate
the requested candidate input directory. The candidate root must exist, must be
a directory, and must not be a symlink. Traversal never follows symlinks and
fails closed on symlinked files or directories inside the bounded traversal.
Traversal is bounded by admitted max files, admitted max total bytes, and
admitted max depth. If a limit would be exceeded, the runner writes only a
blocked runner receipt and no actual iteration artifacts. Candidate artifacts
contain bounded metadata and SHA-256 hashes only; they do not include raw file
content, previews, extracted text, or media organizer metadata.

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

Successful execution records
`runner_status: next_bounded_smoke_iteration_runner_completed`,
`runner_decision: executed_bounded_smoke_iteration_under_admitted_limits`, and
`next_allowed_action: review_next_bounded_smoke_iteration_run`. The result is
review-only: it does not approve production scan, grant production promotion,
move, rename, delete, deduplicate, organize media, copy raw private content,
use network access, call model APIs, invoke external runtimes, add automatic
approval, or grant autonomy.

## Model Workflows

Deterministic mock:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-model-fixture \
  --input-artifact-path /path/to/input.json \
  --output-dir /path/to/output \
  --schema-name job_route_classification_v1
```

Live provider dry-run boundary:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-model-provider-dry-run \
  --input-artifact-path /path/to/input.json \
  --output-dir /path/to/output \
  --schema-name job_route_classification_v1 \
  --provider-id openai
```

The dry-run path does not call the provider and does not persist or log API
keys.

## Browser Workflows

Local fixture:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-browser-fixture \
  --fixture-path /path/to/fixture.html \
  --actions-path /path/to/actions.json \
  --output-dir /path/to/output
```

Dry-run real browser boundary:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-browser-dry-run \
  --actions-path /path/to/actions.json \
  --target-url http://127.0.0.1 \
  --output-dir /path/to/output
```

Only loopback targets and allowlisted actions are accepted. No real browser is
launched.

## ComfyUI Dry Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-comfyui-dry-run \
  --workflow-path /path/to/workflow.json \
  --input-asset /path/to/asset.png \
  --output-dir /path/to/output
```

Validates the workflow fixture, hashes input assets, writes preview evidence,
and writes a loopback endpoint dry-run plan. No endpoint call is made.

## Blender Dry Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-blender-dry-run \
  --scene-path /path/to/scene.blend \
  --operation-plan-path /path/to/plan.json \
  --output-dir /path/to/output
```

Validates the operation plan, hashes the scene, writes preview evidence, and
writes a dry-run plan. Blender is not launched.

## Creative Handoff

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-creative-handoff \
  --family blender_python_mcp \
  --source-asset /path/to/source.blend \
  --output-dir /path/to/output \
  --package-id review-handoff
```

Supported families are:

- `after_effects_extendscript_uxp_aerender`
- `unreal_python_editor_utility_commandlet`
- `houdini_hom_hython_hda`
- `zbrush_support_handoff`
- `blender_python_mcp`
- `comfyui_workflow_api`

The handoff package contains manifests and human instructions only. It does
not control external creative software.

## Task Graph

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-task-graph \
  --graph-path /path/to/task_graph.json \
  --output-dir /path/to/output
```

Task graphs can run fixture/mock execution or dry-run planning. Real runtime
activation requires separate admission and remains fail-closed by default.

Task graphs can include a controlled local asset scan node:

```json
{
  "node_id": "scan_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_scan",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "input_dir": "/path/to/assets",
    "output_dir": "/path/to/asset-scan-output",
    "previous_scan_output_dir": "/path/to/previous-asset-scan-output",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project"
  }
}
```

The node runs the existing `launch-local-asset-scan` launcher path and keeps
the same operational-control behavior. On success, the node record references
`asset_scan_run_receipt.json`, `artifact_index.json`,
`artifact_index_manifest.json`, `local_asset_index.sqlite`,
`local_asset_sqlite_index_manifest.json`,
`local_asset_sqlite_query_summary.md`,
`local_asset_incremental_scan_plan.json`,
`local_asset_incremental_scan_manifest.json`,
`local_asset_incremental_scan_summary.md`, the incremental plan mode, indexed
artifact counts, quarantine counts, and replay hints. On failure, the graph is
marked failed, writes
`task_graph_failure_bundle.json`, records the failed `node_id` and
`failure_stage`, and preserves any safe local asset scan failure bundle in the
node `output_dir`. Dependent nodes are skipped after a failed dependency.

The task graph replay manifest binds node output references by hash and does
not embed raw file contents or private asset contents. The node still requires
human approval and does not add UI, desktop behavior, global SQLite storage,
Operator Console behavior, real-folder smoke, network access, model API calls,
external runtime activation, input mutation, file movement, file renaming,
duplicate deletion, media organizer behavior, or production autonomy.

Task graphs can also include a local asset smoke readiness node:

```json
{
  "node_id": "preflight_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_readiness",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "candidate_input_dir": "/path/to/candidate-assets",
    "output_dir": "/path/to/smoke-readiness-output",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_entries": 50000,
    "max_depth": 20,
    "max_total_bytes": 500000000000
  }
}
```

The node runs `launch-local-asset-smoke-readiness` and records the readiness
report, manifest, summary, artifact index paths, readiness status, readiness
decision, count estimates, and explicit false values for real scan execution,
file hashing, raw content reads, input mutation, and external runtime
activation. It is still review-only and requires human approval before any
future real-folder smoke.

Task graphs can include a human-approved bounded local asset smoke node:

```json
{
  "node_id": "human_smoke_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_human_smoke_run",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "candidate_input_dir": "/path/to/candidate-assets",
    "output_dir": "/path/to/human-smoke-output-root",
    "readiness_report": "/path/to/readiness/local_asset_smoke_readiness_report.json",
    "human_approval_id": "reviewer-ticket-123",
    "human_approval_phrase": "I_APPROVE_LOCAL_ASSET_SMOKE_RUN",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_smoke_files": 25,
    "max_smoke_bytes": 100000000,
    "max_smoke_depth": 4,
    "previous_scan_output_dir": "/path/to/previous-scan-output"
  }
}
```

The node runs the same `launch-local-asset-human-smoke-run` launcher path and
records approval, admission receipt, smoke summary, control and scan output
directories, readiness status and decision, admission status, scan invocation
status, scan completion, bounded smoke status, and explicit false values for
production scan, input mutation, network access, model API calls, and external
runtime invocation.

Task graphs can include a post-smoke-run review packet node:

```json
{
  "node_id": "review_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_review_packet",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "smoke_output_dir": "/path/to/human-smoke-output-root",
    "output_dir": "/path/to/review-packet-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-review-packet` and records the packet,
manifest, summary, decision checklist, artifact index paths, review packet
status, recommended human decision, and explicit false values for scan
execution, readiness execution, raw candidate content reads, candidate file
hashing, smoke output mutation, input mutation, file movement, file renaming,
file deletion, duplicate deletion, media organizer behavior, network access,
model API calls, and external runtime invocation.

Task graphs can include a local asset smoke promotion gate node:

```json
{
  "node_id": "promote_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "review_output_dir": "/path/to/review-packet-output",
    "output_dir": "/path/to/promotion-gate-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-promotion-gate` and records the
decision, gate manifest, summary, human signoff checklist, artifact index
paths, promotion gate status, promotion decision, next bounded smoke
iteration allowance, blocker list, and explicit false values for scan
execution, readiness execution, human smoke execution, review packet mutation,
raw candidate content reads, candidate file hashing, production promotion, and
production scan approval.

Task graphs can include a bounded smoke iteration node:

```json
{
  "node_id": "iterate_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_bounded_smoke_iteration",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "promotion_output_dir": "/path/to/promotion-gate-output",
    "candidate_input_dir": "/path/to/candidate-assets",
    "readiness_report": "/path/to/readiness/local_asset_smoke_readiness_report.json",
    "output_dir": "/path/to/iteration-output",
    "human_signoff_id": "reviewer-ticket-456",
    "human_signoff_phrase": "I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_smoke_files": 100,
    "max_smoke_bytes": 1073741824,
    "max_smoke_depth": 12,
    "previous_scan_output_dir": "/path/to/previous-scan-output"
  }
}
```

The node runs `launch-local-asset-bounded-smoke-iteration` and records the
iteration result, manifest, summary, human review checklist, signoff,
admission, artifact index paths, iteration status and decision, bounded smoke
iteration status, and explicit false values for production promotion,
production scan approval, production scan execution, automatic approval,
watcher/daemon behavior, input mutation, file movement, file renaming, file
deletion, duplicate deletion, media organizer behavior, network access, model
API calls, and external runtime invocation.

Task graphs can include a bounded smoke iteration review packet node:

```json
{
  "node_id": "review_iteration",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_iteration_review_packet",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "iteration_output_dir": "/path/to/iteration-output",
    "output_dir": "/path/to/iteration-review-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-iteration-review-packet` and records
the packet, manifest, summary, decision checklist, artifact index paths,
iteration review status, recommended human decision, iteration status,
bounded smoke iteration status, smoke completion, scan completion, and
explicit false values for production promotion, production scan approval,
production scan execution, scan execution by the review packet, readiness
execution, human smoke execution, bounded iteration execution by the review
packet, promotion gate execution, raw candidate content reads, candidate file
hashing, input mutation, iteration output mutation, smoke output mutation,
file movement, file renaming, file deletion, duplicate deletion, media
organizer behavior, network access, model API calls, and external runtime
invocation.

Task graphs can include a local asset iteration promotion gate node:

```json
{
  "node_id": "promote_iteration",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_iteration_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "iteration_review_output_dir": "/path/to/iteration-review-output",
    "output_dir": "/path/to/iteration-promotion-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-iteration-promotion-gate` and records the
decision, gate manifest, summary, human signoff checklist, artifact index
paths, iteration promotion gate status, iteration promotion decision, next
bounded smoke iteration allowance, blocker list, and explicit false values
for production promotion, production scan approval, production scan execution,
scan execution by the gate, readiness execution, human smoke execution,
bounded smoke iteration execution by the gate, iteration review packet
execution by the gate, iteration review output mutation, raw candidate content
reads, candidate file hashing, input mutation, file movement, file renaming,
file deletion, duplicate deletion, media organizer behavior, network access,
model API calls, and external runtime invocation.

Task graphs can include a bounded smoke cycle contract node:

```json
{
  "node_id": "bind_cycle_contract",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_bounded_smoke_cycle_contract",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "readiness_output_dir": "/path/to/readiness-output",
    "smoke_output_dir": "/path/to/initial-smoke-output",
    "smoke_review_output_dir": "/path/to/smoke-review-output",
    "smoke_promotion_output_dir": "/path/to/smoke-promotion-output",
    "iteration_output_dir": "/path/to/iteration-output",
    "iteration_review_output_dir": "/path/to/iteration-review-output",
    "iteration_promotion_output_dir": "/path/to/iteration-promotion-output",
    "output_dir": "/path/to/cycle-contract-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-bounded-smoke-cycle-contract` and records
the contract, manifest, summary, human review checklist, artifact index paths,
cycle contract status, cycle contract decision, next allowed action, blocker
count, human review flags, and explicit false boundary flags. It remains a
metadata-only synthesis node and does not execute any upstream runtime stage.

Task graphs can include a bounded smoke cycle human review node:

```json
{
  "node_id": "review_cycle_contract",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_bounded_smoke_cycle_human_review",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "cycle_contract_output_dir": "/path/to/cycle-contract-output",
    "output_dir": "/path/to/cycle-human-review-output",
    "human_review_id": "review-001",
    "human_reviewer_id": "reviewer-001",
    "human_decision": "approve_cycle_contract_for_next_bounded_smoke_iteration",
    "human_signoff_phrase": "I_REVIEWED_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT",
    "project_id": "demo_project",
    "human_review_notes": "optional notes"
  }
}
```

The node runs `launch-local-asset-bounded-smoke-cycle-human-review` and
records the human review decision, manifest, summary, checklist, artifact
index paths, human review status, human review decision, next allowed action,
prepare allowance, execute denial, human review flags, and explicit false
boundary flags. It records review metadata only and does not execute cycle
contract generation or the next bounded smoke iteration.

Task graphs can include a next bounded smoke iteration admission node:

```json
{
  "node_id": "admit_next_iteration_prepare",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_admission",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "cycle_human_review_output_dir": "/path/to/cycle-human-review-output",
    "output_dir": "/path/to/next-admission-output",
    "project_id": "demo_project",
    "requested_next_iteration_id": "iteration-002",
    "operator_notes": "optional notes"
  }
}
```

The node runs
`launch-local-asset-next-bounded-smoke-iteration-admission` and records the
admission receipt, manifest, summary, checklist, artifact index paths,
admission status, admission decision, next allowed action, prepare admission,
execute denial, human review requirements, and explicit false boundary flags.
It records prepare-only permission metadata and does not execute the next
bounded smoke iteration or create the next iteration output directory.

Task graphs can include a next bounded smoke iteration execution request node:

```json
{
  "node_id": "request_next_iteration_execution",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_execution_request",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "next_admission_output_dir": "/path/to/next-admission-output",
    "output_dir": "/path/to/execution-request-output",
    "project_id": "demo_project",
    "request_id": "request-002",
    "operator_id": "operator-001",
    "operator_notes": "optional notes",
    "requested_next_iteration_id": "iteration-002",
    "requested_candidate_input_dir": "/path/to/future-candidate-input",
    "requested_next_iteration_output_dir": "/path/to/future-iteration-output",
    "requested_max_files": 25,
    "requested_max_total_bytes": 104857600,
    "requested_max_depth": 4,
    "requested_compare_previous_scan_manifest_path": "/path/to/previous/asset_manifest.json",
    "requested_previous_iteration_artifact_index_path": "/path/to/previous/artifact_index.json"
  }
}
```

The node runs
`launch-local-asset-next-bounded-smoke-iteration-execution-request` and records
the request, manifest, summary, checklist, artifact index paths, request
status, request decision, next allowed action, requested metadata and limits,
future request creation flag, execute denial, next-iteration execution/output
denial, candidate access denial, human approval/review requirements, and
explicit false boundary flags. It records request metadata only and does not
execute the next bounded smoke iteration or create the requested next
iteration output directory.

Task graphs can include a next bounded smoke iteration runner admission node:

```json
{
  "node_id": "admit_next_iteration_runner",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_runner_admission",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "execution_request_output_dir": "/path/to/execution-request-output",
    "output_dir": "/path/to/runner-admission-output",
    "project_id": "demo_project",
    "runner_admission_id": "runner-admission-002",
    "runner_operator_id": "operator-001",
    "runner_operator_acknowledgement_phrase": "I_ACKNOWLEDGE_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ONLY",
    "admitted_runner_id": "bounded-smoke-runner",
    "admitted_runner_version": "1.0.0",
    "admitted_max_files": 25,
    "admitted_max_total_bytes": 104857600,
    "admitted_max_depth": 4,
    "operator_notes": "optional notes",
    "runner_environment_label": "local-fixture"
  }
}
```

The node runs
`launch-local-asset-next-bounded-smoke-iteration-runner-admission` and records
the runner admission, manifest, summary, checklist, artifact index paths,
admission status, admission decision, next allowed action, runner consume
admission, runner execution denial, next-iteration execution/output denial,
candidate access denial, human approval/review requirements, and explicit
false boundary flags. It stores only the runner acknowledgement hash and does
not execute the runner, execute the next bounded smoke iteration, create the
next iteration output directory, approve production scanning, or access
candidate paths.

Task graphs can include a next bounded smoke iteration runner node:

```json
{
  "node_id": "execute_next_iteration_runner",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_runner",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "runner_admission_output_dir": "/path/to/runner-admission-output",
    "runner_output_dir": "/path/to/runner-output",
    "actual_next_iteration_output_dir": "/path/to/future-iteration-output",
    "runner_execution_id": "runner-execution-002",
    "runner_operator_id": "operator-001",
    "runner_execution_acknowledgement_phrase": "I_EXECUTE_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_UNDER_ADMITTED_LIMITS",
    "project_id": "demo_project",
    "operator_notes": "optional notes"
  }
}
```

The node runs
`launch-local-asset-next-bounded-smoke-iteration-runner` and records the runner
receipt paths, actual iteration artifact list, runner status, runner decision,
next allowed action, execution flags, candidate bounded metadata totals,
admitted/requested limits, human approval/review requirements, and explicit
false production, autonomy, mutation, media organizer, network, model, and
external runtime flags.

## Next Bounded Smoke Iteration Run Review Packet

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-run-review-packet \
  --runner-output-dir /path/to/runner-output \
  --actual-next-iteration-output-dir /path/to/actual-next-iteration-output \
  --output-dir /path/to/run-review-packet-output \
  --review-packet-id run-review-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

The run review packet is a generated-artifacts-only, non-executing review
layer after the next bounded smoke iteration runner. It consumes only the
runner output directory and the actual next iteration output directory. The
output directory must already exist, and all review packet writes are
exclusive and fail closed on existing files.

Required source artifacts from the runner output directory are:

- `local_asset_next_bounded_smoke_iteration_runner.json`
- `local_asset_next_bounded_smoke_iteration_runner_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional runner source artifacts are the runner summary and checklist
markdown files. Required source artifacts from the actual next iteration
output directory are:

- `local_asset_next_bounded_smoke_iteration_run.json`
- `local_asset_next_bounded_smoke_iteration_run_manifest.json`
- `local_asset_next_bounded_smoke_iteration_candidate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional actual iteration source artifacts are the iteration summary and
checklist markdown files. The review packet verifies generated type fields,
manifest hashes, artifact index hashes, runner/run/candidate consistency,
candidate counts, byte totals, max depth, admitted limits, requested paths,
bounded file records, and the runner manifest's actual-iteration artifact
bindings.

The review packet is ready only when the runner and actual run record show
`next_bounded_smoke_iteration_runner_completed`,
`executed_bounded_smoke_iteration_under_admitted_limits`, and
`review_next_bounded_smoke_iteration_run`; the runner execution and next
iteration execution flags are true; output directory creation flags are
false; candidate limits were enforced; candidate symlinks are empty; bounded
file records are deterministic metadata-only records; source artifacts are
trusted; and there are no missing artifacts, untrusted artifacts, source
boundary violations, or cross-artifact inconsistencies.

The command emits:

- `local_asset_next_bounded_smoke_iteration_run_review_packet.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

The artifact index binds only the four review packet artifacts and does not
recursively index runner output, actual iteration output, upstream cycle
outputs, or candidate input files.

This review layer does not re-run the runner, run candidate discovery,
validate live candidate paths, list candidate directories, read raw candidate
contents, hash live candidate files, create source output directories, mutate
upstream outputs, move/rename/delete files, deduplicate files, add media
organizer behavior, approve promotion, approve production scanning, grant
production promotion, use network access, call model APIs, invoke external
runtimes, add UI, add Operator Console behavior, add watcher behavior, or
grant autonomy. A ready packet only routes to the later separate promotion
gate action `run_next_bounded_smoke_iteration_run_promotion_gate`.

Task graphs can include a next bounded smoke iteration run review packet node:

```json
{
  "node_id": "review_next_iteration_run",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_run_review_packet",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "runner_output_dir": "/path/to/runner-output",
    "actual_next_iteration_output_dir": "/path/to/actual-next-iteration-output",
    "output_dir": "/path/to/run-review-packet-output",
    "review_packet_id": "run-review-002",
    "project_id": "demo_project",
    "reviewer_id": "reviewer-001",
    "operator_notes": "optional notes"
  }
}
```

The node records the review packet, manifest, summary, checklist, artifact
index paths, review status, review decision, next allowed action, inherited
runner and request metadata, human approval/review requirements, and explicit
false flags for runner re-execution, candidate access by review, production
approval, mutation/deletion, media organizer behavior, network, model, and
external runtime use.

## Next Bounded Smoke Iteration Run Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate \
  --run-review-packet-output-dir /path/to/run-review-packet-output \
  --output-dir /path/to/run-promotion-gate-output \
  --promotion-gate-id run-promotion-gate-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

Required arguments are `--run-review-packet-output-dir`, `--output-dir`, and
`--promotion-gate-id`. Optional arguments are `--project-id`, `--reviewer-id`,
and `--operator-notes`. The output directory must already exist and must not
be the source review packet directory, inside it, or contain it. All writes
are exclusive and fail closed on existing files or symlink collisions.

The gate consumes generated run review packet artifacts only. Required source
artifacts are:

- `local_asset_next_bounded_smoke_iteration_run_review_packet.json`
- `local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional source artifacts are the generated run review packet summary and
checklist markdown files. The gate verifies generated type fields, the review
packet manifest's packet, summary, and checklist hashes, and the source
artifact index manifest's artifact index hash. Malformed JSON, symlink source
artifacts, missing required type fields, and hash mismatches are untrusted.

The promotion gate is ready only when the source review packet has
`review_status =
next_bounded_smoke_iteration_run_review_packet_ready`,
`review_decision =
package_next_bounded_smoke_iteration_run_for_promotion_gate_review`, and
`next_allowed_action =
run_next_bounded_smoke_iteration_run_promotion_gate`; all cross-artifact
checks passed; review blockers, missing required artifacts, and untrusted
artifacts are empty; deterministic ordering is true; source boundary booleans
are present and type-correct; runner execution and next bounded smoke
iteration execution are already true in the reviewed run facts; candidate
limits were enforced; candidate symlink metadata is empty; candidate counts,
total bytes, and max depth are non-negative integers; and bounded file records
are sorted metadata-only records.

When ready, the gate emits `gate_status =
next_bounded_smoke_iteration_run_promotion_gate_ready`, `gate_decision =
approve_next_bounded_smoke_iteration_run_for_cycle_contract`, and
`next_allowed_action = create_next_bounded_smoke_cycle_contract_from_run`.
This is bounded-run promotion only. It allows a later separate
cycle-contract-generation command to consume the gate, but it does not
generate the cycle contract.

The command emits:

- `local_asset_next_bounded_smoke_iteration_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

The artifact index binds only the four promotion gate artifacts. It does not
recursively index the review packet output, runner output, actual iteration
output, upstream cycle outputs, or candidate input files.

This gate does not access live candidate paths. It does not validate candidate
paths, list candidate directories, read candidate file contents, or hash
candidate input files. It does not re-run the runner, regenerate the review
packet, run readiness, run human smoke, run smoke review, run smoke promotion,
run bounded smoke iteration, run iteration review, run iteration promotion,
generate cycle contracts, mutate upstream outputs, move/rename/delete files,
deduplicate files, copy raw private content, add media organizer behavior, use
network access, call model APIs, invoke external runtimes, approve production
scanning, grant production promotion, add UI, add Operator Console behavior,
add watcher/daemon behavior, perform automatic approval, or grant autonomy.

Task graphs can include a next bounded smoke iteration run promotion gate node:

```json
{
  "node_id": "promote_next_iteration_run",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "run_review_packet_output_dir": "/path/to/run-review-packet-output",
    "output_dir": "/path/to/run-promotion-gate-output",
    "promotion_gate_id": "run-promotion-gate-002",
    "project_id": "demo_project",
    "reviewer_id": "reviewer-001",
    "operator_notes": "optional notes"
  }
}
```

The node records the promotion gate, manifest, summary, checklist, artifact
index paths, gate status, gate decision, next allowed action, inherited
review/runner/request metadata, bounded-run promotion approval,
cycle-contract-generation allowance with `cycle_contract_generated=false`,
human approval/review requirements, and explicit false flags for candidate
access by gate, runner re-execution, production scan approval, production
promotion, mutation/deletion, media organizer behavior, network, model, and
external runtime use.

## Next Bounded Smoke Cycle Contract From Run Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate \
  --run-promotion-gate-output-dir /path/to/run-promotion-gate-output \
  --output-dir /path/to/next-cycle-contract-output \
  --cycle-contract-id next-cycle-contract-002 \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

Required arguments are `--run-promotion-gate-output-dir`, `--output-dir`, and
`--cycle-contract-id`. Optional arguments are `--project-id`, `--reviewer-id`,
and `--operator-notes`. The output directory must already exist, must not be
the source run promotion gate directory, must not be inside it, and must not
contain it. Expected output files are written exclusively and existing files
or symlink collisions fail closed.

This command consumes generated output from the next bounded smoke iteration
run promotion gate only. Required source artifacts are:

- `local_asset_next_bounded_smoke_iteration_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional source artifacts are the generated promotion gate summary and
checklist markdown files. The contract verifies generated type fields, the
promotion gate manifest's gate, summary, and checklist hashes when those
artifacts are present, and the source artifact index manifest's artifact
index hash. Missing required source artifacts, malformed JSON, source
artifact symlinks, type mismatches, and hash mismatches block the contract.

The contract is ready only when the source gate has `gate_status =
next_bounded_smoke_iteration_run_promotion_gate_ready`, `gate_decision =
approve_next_bounded_smoke_iteration_run_for_cycle_contract`, and
`next_allowed_action = create_next_bounded_smoke_cycle_contract_from_run`;
bounded run promotion and cycle contract generation are allowed; the source
gate has no blockers, missing required artifacts, or untrusted artifacts; all
required source boundary booleans are present, type-correct, and still false;
human approval/review and deterministic ordering remain true; and inherited
run facts are valid metadata-only records.

When ready, the contract emits `contract_status =
next_bounded_smoke_cycle_contract_ready`, `contract_decision =
create_bounded_smoke_cycle_contract_from_approved_run`, and
`next_allowed_action =
submit_next_bounded_smoke_cycle_contract_for_human_review`. This is still not
production approval. It only packages the approved bounded run into the next
cycle-contract artifact so a later human review/admission step can decide
whether the next bounded cycle may proceed.

The command emits:

- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

The artifact index binds only the four cycle-contract artifacts. It does not
recursively index the run promotion gate output, run review packet output,
runner output, actual iteration output, or candidate input files.

This contract does not access live candidate paths. It does not validate
candidate paths, list candidate directories, read candidate file contents, or
hash candidate input files. It does not execute the runner, regenerate the run
review packet, re-run the run promotion gate, create a production gate, run a
production scan, grant production promotion, mutate upstream outputs,
move/rename/delete files, deduplicate files, add media organizer behavior,
copy raw private content, add UI, add Operator Console behavior, add
watcher/daemon behavior, use network access, call model APIs, invoke external
runtimes, perform automatic approval, or grant autonomy.

Task graphs can include a next bounded smoke cycle contract-from-run-gate
node:

```json
{
  "node_id": "create_next_cycle_contract",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "run_promotion_gate_output_dir": "/path/to/run-promotion-gate-output",
    "output_dir": "/path/to/next-cycle-contract-output",
    "cycle_contract_id": "next-cycle-contract-002",
    "project_id": "demo_project",
    "reviewer_id": "reviewer-001",
    "operator_notes": "optional notes"
  }
}
```

The node records the cycle contract, manifest, summary, checklist, artifact
index paths, contract status, contract decision, next allowed action, source
gate readiness metadata, inherited review/runner/request metadata, human
approval/review requirements, and explicit false flags for runner execution by
contract, review packet generation by contract, run promotion gate
re-execution, candidate access by contract, production scan approval,
production promotion, mutation/deletion, media organizer behavior, network,
model, and external runtime use.

## Next Bounded Smoke Cycle Contract Human Review From Run Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate \
  --cycle-contract-output-dir /path/to/next-cycle-contract-output \
  --output-dir /path/to/next-cycle-contract-human-review-output \
  --human-review-id next-cycle-contract-review-002 \
  --human-decision approve_next_bounded_smoke_cycle_contract_for_bounded_admission \
  --human-signoff-phrase I_REVIEWED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE \
  --project-id demo_project \
  --reviewer-id reviewer-001 \
  --operator-notes "optional notes"
```

Required arguments are `--cycle-contract-output-dir`, `--output-dir`, and
`--human-review-id`, `--human-decision`, and `--human-signoff-phrase`.
Optional arguments are `--project-id`, `--reviewer-id`, and
`--operator-notes`. The canonical signoff phrase is exactly
`I_REVIEWED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE`.
The output directory must already exist, must not be the source cycle
contract directory, must not be inside it, and must not contain it. Expected
output files are written exclusively and existing files or symlink collisions
fail closed.

This command consumes generated output from
`launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate`
only. Required source artifacts are the cycle contract JSON, its manifest, the
source `artifact_index.json`, and the source `artifact_index_manifest.json`.
Optional source summary/checklist markdown files must be hash-bound by the
source manifest when present.

Allowed bounded `--human-decision` values are:

- `approve_next_bounded_smoke_cycle_contract_for_bounded_admission`
- `stop_cycle`
- `repair_artifacts`
- `repair_cycle_contract`
- `reject_boundary_violation`

When the source contract is ready, the human decision is exactly
`approve_next_bounded_smoke_cycle_contract_for_bounded_admission`, and the
signoff phrase exactly matches the canonical phrase, it emits
`human_review_status =
next_bounded_smoke_cycle_contract_human_review_ready`,
`human_review_decision =
approve_next_bounded_smoke_cycle_contract_for_bounded_admission`, and
`next_allowed_action =
admit_next_bounded_smoke_cycle_contract_for_later_execution_request`.
This is bounded-admission-only. It does not execute the next cycle and it is
not production approval.

Missing or invalid human decisions, missing or wrong signoff phrases, and
non-approve bounded decisions do not allow bounded admission. The review
stores `human_signoff_phrase_sha256` and
`human_signoff_phrase_persisted=false`; it does not persist the plaintext
signoff phrase.

The command emits:

- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate.json`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest.json`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary.md`
- `local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

The artifact index binds only the four human-review artifacts. The command
does not recursively index the source cycle contract output or candidate input
files, does not read live candidate paths, does not regenerate the cycle
contract, does not execute a runner, does not create a production gate, does
not approve production scanning, and does not grant production promotion.

Task graphs can include a next bounded smoke cycle contract human-review node:

```json
{
  "node_id": "review_next_cycle_contract",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "cycle_contract_output_dir": "/path/to/next-cycle-contract-output",
    "output_dir": "/path/to/next-cycle-contract-human-review-output",
    "human_review_id": "next-cycle-contract-review-002",
    "human_decision": "approve_next_bounded_smoke_cycle_contract_for_bounded_admission",
    "human_signoff_phrase": "I_REVIEWED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE",
    "project_id": "demo_project",
    "reviewer_id": "reviewer-001",
    "operator_notes": "optional notes"
  }
}
```

The node records the human review, manifest, summary, checklist, artifact
index paths, explicit `human_decision`, signoff hash/persistence metadata,
source contract status/decision/action, inherited
review/runner/request metadata, bounded-cycle admission allowance, human
approval/review requirements, and explicit false flags for runner execution
by human review, cycle contract re-execution, candidate access by human
review, production scan approval, production promotion, mutation/deletion,
media organizer behavior, network, model, and external runtime use.

Task graph execution now also emits `task_graph_artifact_outputs.json` in the
graph `output_dir` after node execution. This manifest is a graph-level,
metadata-only, non-authoritative artifact binding surface. It records
node-produced artifact paths, existence, file sizes, and SHA-256 hashes for
already-produced artifacts, plus the graph-level execution, replay, and failure
manifests when present.

`task_graph_artifact_outputs.json` does not copy raw private asset contents,
does not index raw content, does not mutate inputs, and does not move, rename,
delete, deduplicate, or organize media files. It does not add UI, desktop app
behavior, global SQLite storage, Operator Console behavior, network access,
model API calls, browser runtime activation, or external creative runtime
activation.

## Delivery Validation

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-runtime-delivery-validation \
  --package-dir /path/to/delivery-package \
  --output-dir /path/to/output
```

Validates package manifest hashes, replay metadata, and leakage sentinels.

## Product Health

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-product-health-check \
  --output-dir /path/to/output
```

Reports dependency state, adapter registry health, runtime admission defaults,
deferred runtimes, launcher workflow coverage, docs state, and Personal AI test
metadata.

## Default Runtime Posture

The product-complete system is local-first and fail-closed. Live model calls,
real browser execution, ComfyUI endpoint submission, Blender subprocess
execution, and external creative software control are intentionally not
activated by default.
