# Shot Assistant And Templates V1

## Purpose

Use the shot assistant to turn a scanned asset library into a practical shot
plan. The planner does not render or generate images. It selects candidate
assets, reports missing required assets, and emits manual plus optional
approval-gated runner steps.

## Templates

- `energy-impact`
- `smoke-dust`
- `portal-lightning`
- `editorial-handoff`

List templates:

```bash
python3 seos.py creative shot templates
```

## Build A Plan

```bash
python3 seos.py creative shot plan \
  --template energy-impact \
  --shot-id SHOT_ENERGY_IMPACT_FIXTURE \
  --registry-json reports/creative/assets/asset_library_report_v1.json \
  --tool-health-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json \
  --adapter-contracts-json reports/creative/adapters/optional_adapter_contracts_v1.json \
  --output-json reports/creative/shots/shot_plan_energy_impact_v1.json \
  --output-md reports/creative/shots/shot_plan_energy_impact_v1.md
```

## Contract Boundary

- Read-only over the asset report.
- Does not launch DCC tools, ComfyUI, or Houdini.
- Does not create renders, comps, exports, archives, or media files.
- Does not mutate the asset library.
- Optional runner commands are command templates only and still require explicit
  local execution approval.
- Final creative approval remains human-owned.

## Validation

```bash
make creative-shot-planner-check
python3 -m unittest discover -s tests/creative -p 'test_shot_planner_v1.py' -v
python3 scripts/creative_no_local_path_leak_check_v3.py
python3 scripts/creative_public_release_check_v3.py
```
