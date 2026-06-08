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

## Step 3: Local Production Dashboard

Status: implemented by the Step 3A slice.

Turn scan, search, and tool-health results into one operator dashboard with
category counts, largest folders, duplicate groups, archive warnings, texture
set status, likely incomplete packs, and next actions.

Validation:

```bash
make creative-production-dashboard-check
python3 seos.py creative production-dashboard --registry-json reports/creative/assets/asset_library_report_v1.json --output-md reports/creative/assets/local_production_dashboard_v1.md --output-html reports/creative/assets/local_production_dashboard_v1.html
```

## Step 4: Real Local Tool Execution

Add only truthful optional adapters. Houdini and ComfyUI should produce real
evidence where available and unavailable/license-blocked evidence otherwise.
Default CI must use mocks or unavailable behavior.

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
