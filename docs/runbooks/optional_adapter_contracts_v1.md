# Optional Adapter Contracts V1

## Purpose

Use this report before adding any new Blender, After Effects, DaVinci Resolve,
Unreal Engine, or ZBrush execution runner. It records what SEOS can truthfully
claim today, what remains blocked, and what real local proof a future runner
must produce.

## Operator Command

```bash
python3 seos.py creative optional-adapter-contracts \
  --mode public \
  --doctor-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json \
  --output-json reports/creative/adapters/optional_adapter_contracts_v1.json \
  --output-md reports/creative/adapters/optional_adapter_contracts_v1.md
```

The command also works as:

```bash
python3 seos.py creative adapter contracts
```

## Contract Boundary

- The report is read-only.
- It does not launch DCC applications.
- It does not submit render, generation, import, export, commandlet, or GUI jobs.
- It does not install plugins, download models, use external networks, or check
  out licenses by default.
- It never marks `supports_execute` as true.
- It uses tool-health discovery and existing adapter artifacts to decide the
  next truthful proof required for each adapter.

## Covered Adapters

- Blender: background Python smoke remains the next proof.
- After Effects: fixed aerender/app-version smoke remains the next proof.
- DaVinci Resolve: read-only scripting smoke remains the next proof.
- Unreal Engine: fixed commandlet help/version smoke remains the next proof.
- ZBrush: manual export handoff verification remains the next proof; no default
  automated ZBrush runner is claimed.

## Validation

```bash
make creative-optional-adapter-contracts-check
python3 -m unittest discover -s tests/creative -p 'test_optional_adapter_contracts_v1.py' -v
python3 scripts/creative_no_local_path_leak_check_v3.py
python3 scripts/creative_public_release_check_v3.py
```

Default CI does not require proprietary tools.
