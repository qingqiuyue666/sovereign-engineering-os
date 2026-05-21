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
  --recursive \
  --project-id demo_project
```

Performs a read-only local asset scan. By default it does not scan nested
directories and excludes hidden files; use `--recursive` and `--include-hidden`
only when those paths should be included.

The scan writes reports only to `output_dir` and fails closed if expected
output files already exist. It does not move, rename, delete, or reorganize
input files, and it is not a media organizer. It does not call model APIs, does
not call the network, and does not launch ComfyUI, Blender, Houdini, After
Effects, DaVinci, or a browser.

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
