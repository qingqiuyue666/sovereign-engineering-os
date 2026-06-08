# Real Works Operation V1

Use the real works operation report to keep repeated creative work grounded in
actual project needs. It builds shot plans for the repeated workflows, reads
pressure and hardening status, and lists the next development needs that are
justified by real findings.

Run the fixture-backed operation report:

```bash
python3 seos.py creative works-operation \
  --registry-json reports/creative/assets/asset_library_report_v1.json \
  --tool-health-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json \
  --adapter-contracts-json reports/creative/adapters/optional_adapter_contracts_v1.json \
  --pressure-json reports/creative/pressure/real_project_pressure_test_v1.json \
  --hardening-json reports/creative/hardening/production_hardening_plan_v1.json \
  --output-json reports/creative/operation/real_works_operation_v1.json \
  --output-md reports/creative/operation/real_works_operation_v1.md
```

The report covers:

- energy impact;
- smoke/dust;
- portal/lightning;
- asset library;
- editorial handoff;
- pressure status;
- hardening status;
- repeated operation commands;
- development needs tied to pressure findings, hardening actions, or workflow
  blockers.

## Boundaries

The operation report is read-only. It does not mutate assets, delete
duplicates, copy packages, launch DCC tools, submit AI jobs, render, simulate,
generate, export, or approve final production work. Optional runners remain
separate approval-gated commands.

## Validation

```bash
make creative-real-works-operation-check
```
