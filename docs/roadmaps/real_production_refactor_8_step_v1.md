# Real Production Refactor 8-Step Roadmap v1

## Direction

SEOS must be developed as a useful local AI/VFX production assistant, not as a
self-certification project. Governance remains valuable only where it protects
or explains real local production work.

High-priority work must reduce manual operator effort, produce real local
artifacts, or return truthful failure evidence with clear next actions.

## Product Boundary

- Local-first production assistant and controlled execution/evidence system.
- Not an operating-system sandbox.
- Not uncontrolled RPA or desktop automation.
- Not a cloud production platform.
- Not externally certified.
- Proprietary DCC tools are optional and must never be required by default CI.
- Missing tools and license blocks must produce truthful unavailable evidence.

## Step 1: Refocus Positioning

Status: started.

README and roadmap language now describe SEOS in terms of practical production
value: local asset scans, useful reports, adapter truthfulness, shot planning,
local outputs, hashes, evidence, replay, and actionable failure bundles.

## Step 2A: Real Local Asset Scanner V1

Status: implemented by the Step 2A slice.

Operator value:

- scan a configurable local asset root;
- classify likely Houdini, Unreal, Blender, ZBrush, After Effects, DaVinci,
  ComfyUI, texture, material, HDRI, cache, model, video, audio, LUT, script,
  archive, and unknown assets;
- detect empty directories;
- detect exact duplicate groups by size and SHA-256;
- detect missing multipart archive parts;
- detect likely texture sets and missing standard maps;
- detect likely model/material/texture production packs;
- emit sanitized JSON and readable Markdown reports;
- keep the asset root read-only.

Validation:

```bash
make creative-real-asset-scanner-check
python3 scripts/creative_asset_scan_v3.py --mode public
python3 scripts/creative_total_check_v3.py
git diff --check
```

## Step 2B: Asset Search / Retrieval CLI V1

Status: implemented by the Step 2B slice.

Queries over the generated registry:

- find usable Houdini FX assets;
- find VDB/cache assets;
- find missing texture sets;
- find duplicate video/audio groups;
- find incomplete archives;
- find empty directories.

Validation:

```bash
make creative-asset-search-check
python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query missing-texture-sets
```

## Step 3A: Local Production Dashboard V1

Status: implemented by the Step 3A slice.

Turn scan, search, and tool-health results into one operator dashboard with
category counts, largest folders, duplicate groups, archive warnings, texture
set status, likely incomplete packs, and next actions. The Step 3A dashboard is
truthful about tool readiness: it reports assets by tool category but does not
pretend tool-health smoke checks have been run.

Validation:

```bash
make creative-production-dashboard-check
python3 seos.py creative production-dashboard --registry-json reports/creative/assets/asset_library_report_v1.json --output-md reports/creative/assets/local_production_dashboard_v1.md --output-html reports/creative/assets/local_production_dashboard_v1.html
```

## Step 3B: Local Tool Health Dashboard V1

Status: implemented by the Step 3B slice.

Operator value:

- report local availability for Python, Python dependencies, Git, FFmpeg,
  Houdini/hython, ComfyUI, Blender, After Effects, DaVinci Resolve, Unreal
  Engine, and ZBrush;
- show found/missing/config-required status;
- show versions and sanitized configured paths where detectable;
- distinguish smoke-passed, path-detected, app-detected, config-required,
  environment-not-found, and license-blocked style evidence;
- produce JSON, Markdown, and HTML reports;
- avoid launching DCC or AI tools and avoid checking out licenses;
- keep proprietary tools optional for default CI.

Validation:

```bash
make creative-tool-health-dashboard-check
python3 seos.py creative tool-health-dashboard --mode public --doctor-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json --output-json reports/creative/tool_health/local_tool_health_dashboard_v1.json --output-md reports/creative/tool_health/local_tool_health_dashboard_v1.md --output-html reports/creative/tool_health/local_tool_health_dashboard_v1.html
```

## Step 4A: Houdini Real Local Runner V1

Status: implemented by the Step 4A slice.

Operator value:

- detect `hython` from explicit `--hython`, `SEOS_HYTHON_PATH`, PATH, or common
  install locations;
- require explicit operator approval before launching `hython`;
- run a fixed minimal SEOS smoke driver, not a user-supplied raw command;
- write one smoke output JSON under the allowed output root;
- hash the output and record a materialization result;
- return `ENV_NOT_FOUND`, `USER_APPROVAL_REQUIRED`, `LICENSE_BLOCKED`,
  `LONG_TASK_BLOCKED`, or `EXECUTION_FAILED` truthfully when execution cannot
  complete;
- avoid requiring Houdini in default CI through mocked tests and deterministic
  unavailable evidence.

Validation:

```bash
make creative-houdini-runner-check
python3 scripts/creative_houdini_hython_smoke_v1.py --hython tests/fixtures/creative/software_discovery/missing_hython --output-root work/creative_runs/houdini_unavailable --observed-at 2026-06-08T00:00:00Z --result-json reports/creative/houdini/hython_smoke_unavailable_v1.json --materialization-json reports/creative/houdini/hython_smoke_materialization_v1.json
```

Residual boundaries:

- real Houdini render execution remains outside this smoke runner;
- license checkout can still fail locally and is reported as `LICENSE_BLOCKED`;
- no default CI path requires proprietary SideFX software.

## Step 4B: ComfyUI Real Local Runner V1

Submit a minimal workflow to a running local ComfyUI service when explicitly
approved, collect output evidence where available, and return
`SERVICE_UNAVAILABLE` or `ENV_NOT_FOUND` truthfully otherwise. Default CI must
use mocked service responses or unavailable behavior.

## Step 4C: Optional Adapter Contracts V1

Add truthful extension contracts for Blender, After Effects, DaVinci Resolve,
Unreal Engine, and ZBrush without requiring proprietary tools in default CI or
claiming execution support before real local evidence exists.

## Step 5: Shot Assistant and Templates

Create shot templates and a planner that binds available scanned assets,
reports missing assets, and emits practical manual and optional execution plans.

## Step 6: Real Project Pressure Testing

Run the asset scan, search, shot planner, and optional local adapters against a
realistic production task. Convert repo-side failures into fixes and regression
tests.

## Step 7: Production Hardening

Improve failure repair suggestions, output packaging, runtime reliability,
private path sanitization, output size limits, scan speed, and repeated-use
operator experience.

## Step 8: Real Works Operation

Use SEOS on repeated energy impact, smoke/dust, portal/lightning, asset-library,
and editorial handoff workflows. Continue development only where real project
needs or failure logs justify it.

## External References Used For Direction

- OpenAssetIO frames asset systems around host tools and managed references.
- MaterialX reinforces material and texture metadata as production-relevant
  data rather than decorative file listings.
- OpenUSD asset resolution reinforces the need for portable asset references.

SEOS does not claim to implement these standards in this step. The scanner uses
their practical direction: relative asset references, explicit traits, and
truthful boundaries.
