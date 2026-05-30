# Local Asset Real Folder Smoke Readiness v1

Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`

Canonical local repository path:
`<repo-root>`

Branch: `feat/local-asset-real-folder-smoke-readiness-v1`

## Objective

Add a metadata-only real-folder smoke readiness harness for local asset
scanning. The harness prepares for a future human-approved real-folder smoke
run by inspecting directory safety, estimating entry counts and file sizes,
classifying path risks, estimating scan cost, and writing review artifacts.

## Changed Files

- `kernel/assets/local_asset_smoke_readiness.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_real_folder_smoke_readiness.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_real_folder_smoke_readiness_v1.md`

## Behavior Added

The new readiness path inspects only filesystem metadata:

- path names
- path type
- directory structure
- file size from stat metadata
- extension
- hidden path status
- symlink status
- unsafe directory names
- secret-looking path names

It writes a readiness report, manifest, summary, and artifact index into a
pre-existing `output_dir`.

## CLI Command

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-readiness \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/output \
  --recursive \
  --include-hidden \
  --project-id demo_project \
  --max-entries 50000 \
  --max-depth 20 \
  --max-total-bytes 500000000000
```

Required arguments are `--candidate-input-dir` and `--output-dir`. Optional
arguments are `--recursive`, `--include-hidden`, `--project-id`,
`--max-entries`, `--max-depth`, and `--max-total-bytes`.

## Readiness Artifact Schema

`local_asset_smoke_readiness_report.json` uses
`report_type = local_asset_real_folder_smoke_readiness_report_v1`,
`authority = non_authority`, and
`execution_capability = real_folder_smoke_readiness_only`.

It records:

- readiness status and readiness decision
- candidate and output paths
- project and traversal options
- safety limits
- inspected entry, file, and directory counts
- estimated total bytes
- estimated 1 MiB hash chunks and hash cost band
- extension counts
- media class counts
- top largest files by metadata
- risk counts and deterministic risk items
- skipped items
- limit and traversal-complete state
- explicit no-scope-expansion flags

`local_asset_smoke_readiness_manifest.json` uses
`manifest_type = local_asset_real_folder_smoke_readiness_manifest_v1`,
records report and summary hashes, artifact roles, deterministic ordering,
`metadata_only = true`, and the same no-scope-expansion flags.

`local_asset_smoke_readiness_summary.md` presents the readiness status,
decision, candidate path, output path, project id, traversal flags, counts,
estimated bytes, hash cost band, extension counts, media class counts, risk
counts, largest files by metadata, explicit non-execution statements, and the
next recommended human-review action.

## Safety Limits

The default safety limits are:

- `max_entries = 50000`
- `max_depth = 20`
- `max_total_bytes = 500000000000`

If a limit is exceeded, the harness writes readiness artifacts with
`readiness_status = blocked_limit_exceeded`,
`readiness_decision = block_future_smoke_until_review`, and returns complete
because the readiness gate successfully blocked the future smoke.

## Risk Classification

Risk items are deterministic records with:

- `relative_path`
- `path_type`
- `risk_type`
- `severity`
- `detail`

Supported risk types are:

- `symlink`
- `secret_looking_path`
- `unsafe_directory`
- `hidden_path`
- `unreadable_entry`
- `unsupported_filesystem_entry`
- `traversal_limit_exceeded`
- `total_size_limit_exceeded`
- `depth_limit_exceeded`
- `output_input_overlap`

Blocking safety risks produce
`readiness_status = blocked_safety_risk`. Hidden-path-only warnings produce
`readiness_status = ready_with_warnings`. Clean metadata inspection produces
`readiness_status = ready`.

## Artifact Index Relationship

After writing readiness artifacts, the launcher builds `artifact_index.json`
and `artifact_index_manifest.json` in the same `output_dir`. The artifact
index includes:

- `local_asset_smoke_readiness_report`
- `local_asset_smoke_readiness_manifest`
- `local_asset_smoke_readiness_summary`

The artifact index remains metadata-only and non-authoritative.

## Task Graph Relationship

Task graphs now support:

- `adapter_id = local_asset_runtime`
- `capability = launch_local_asset_smoke_readiness`

Node inputs are `candidate_input_dir`, `output_dir`, `recursive`,
`include_hidden`, `project_id`, `max_entries`, `max_depth`, and
`max_total_bytes`.

The node delegates to the launcher and exposes readiness report, manifest,
summary, artifact index paths, readiness status, readiness decision, and
explicit false values for real scan execution, file hashing, raw content read,
and input mutation. The graph-level artifact output binding emits
`local_asset_smoke_readiness_report`,
`local_asset_smoke_readiness_manifest`, and
`local_asset_smoke_readiness_summary` artifact roles.

## Failure Behavior

`output_dir` must already exist, be a directory, and not be a symlink. It is
never created automatically. `candidate_input_dir` must exist, be a directory,
and not be a symlink. The candidate and output directories must not overlap in
either direction.

Before writing readiness outputs, the harness fails closed if any expected
readiness output or artifact index output already exists. If `output_dir` is
missing or unsafe, no artifacts are written. If `candidate_input_dir` is
missing or invalid while `output_dir` is safe and empty, the harness writes a
structured `failed_preflight` readiness artifact set and returns incomplete.

## Deterministic Ordering Strategy

Directory entries are inspected in sorted relative-path order. Risk items and
skipped items are sorted by relative path, risk or skip reason, path type, and
detail. Extension counts and media class counts are sorted by key. Largest
files are sorted by descending metadata size and then relative path. JSON
outputs are written with sorted keys.

## Explicit Non-Goals

- No real scan.
- No file hashing.
- No raw content read.
- No raw private content copy.
- No input mutation.
- No file movement.
- No file rename.
- No file delete.
- No duplicate deletion.
- No media organizer behavior.
- No watcher or daemon.
- No global database state.
- No UI.
- No desktop app behavior.
- No Operator Console.
- No network access.
- No model API calls.
- No external runtime activation.
- No ComfyUI, Blender, Houdini, After Effects, or DaVinci activation.
- No HFX change.
- No production autonomy.

## Validation Commands Run

- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`: passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`: passed, 8 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`: passed, 7 tests.
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`: passed, 5 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`: passed, 4 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`: passed, 12 tests.
- `python3 -m unittest discover -s tests/schemas -v`: passed, 133 tests.
- `python3 -m unittest discover -s validation/tests/acceptance -v`: passed, 156 tests.
- `python3 -m unittest discover -s tests/tracer_bullet -v`: passed, 6441 tests, 4 skipped.
- `python3 -m unittest tests.personal_ai.test_product_health_check -v`: passed, 5 tests.
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v`: passed, 8 tests.
- Pre-commit `make ci`: test gates passed; final clean-tree gate failed because this branch still had the intended uncommitted changes.
- Pre-commit `git diff --check`: passed.
- Pre-commit `git status --short`: showed only intended branch files.
- Post-commit `make ci`: passed.
- Post-commit `git diff --check`: passed.
- Post-commit `git status --short`: clean.

## Final Verification State

- Final post-commit `make ci` result: passed.
- Final `git diff --check` result: passed.
- Final `git status --short` result: clean.
- Final branch verification state: green on
  `feat/local-asset-real-folder-smoke-readiness-v1`.

## Next Recommended Branch

`feat/local-asset-human-approved-smoke-run-v1`

Implementation-driven recommendation: keep the next branch limited to an
explicit human-approved smoke run admission artifact and do not add automatic
approval, watcher behavior, cache execution, or production autonomy.
