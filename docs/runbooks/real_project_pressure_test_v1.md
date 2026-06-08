# Real Project Pressure Test V1

Use the pressure test to exercise the practical creative pipeline against a
realistic project task. It scans or loads assets, runs useful asset-search
probes, builds a local production dashboard, builds a shot plan, and reports
what still blocks or weakens production use.

Run the fixture-backed pressure test:

```bash
python3 seos.py creative pressure-test \
  --root tests/fixtures/creative/assets \
  --template energy-impact \
  --shot-id SHOT_PRESSURE_ENERGY_IMPACT_FIXTURE \
  --tool-health-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json \
  --adapter-contracts-json reports/creative/adapters/optional_adapter_contracts_v1.json \
  --output-json reports/creative/pressure/real_project_pressure_test_v1.json \
  --output-md reports/creative/pressure/real_project_pressure_test_v1.md
```

Run the same workflow against a local asset root:

```bash
python3 seos.py creative pressure-test \
  --root /path/to/local/assets \
  --mode public \
  --template energy-impact \
  --shot-id SHOT_LOCAL_PRESSURE_001 \
  --output-json work/creative_runs/pressure/pressure.local.json \
  --output-md work/creative_runs/pressure/pressure.local.md
```

Public mode sanitizes the asset root and asset paths. Local mode is intended
for private operator work only.

## What It Probes

- asset scan summary;
- Houdini FX asset search;
- VDB/cache asset search;
- duplicate video/audio search;
- incomplete archive search;
- empty directory search;
- incomplete production-pack search;
- missing texture-set search;
- production dashboard summary;
- shot-plan completeness;
- optional runner readiness and approval gating;
- optional adapter contract-only boundaries.

## Boundaries

The pressure test is read-only. It does not delete duplicates, extract
archives, mutate assets, launch DCC applications, submit render jobs, submit
ComfyUI prompts, install models, or claim final production approval. Optional
local runners remain separate commands that require explicit approval.

## Validation

```bash
make creative-real-project-pressure-test-check
```
