# Production Hardening V1

Use the production hardening plan after a pressure test. It turns pressure
findings into prioritized repair actions and checks whether the public report
set is ready to hand off or archive.

Run the fixture-backed hardening plan:

```bash
python3 seos.py creative hardening-plan \
  --pressure-json reports/creative/pressure/real_project_pressure_test_v1.json \
  --output-json reports/creative/hardening/production_hardening_plan_v1.json \
  --output-md reports/creative/hardening/production_hardening_plan_v1.md
```

The command reads pressure-test evidence and creates:

- prioritized repair actions;
- a manifest of production reports;
- per-artifact existence, size, digest, and local-path-leak checks;
- package readiness status;
- repeatable next actions for rerunning the pressure test.

## Boundaries

The hardening plan is read-only. It does not copy files, create archives, delete
duplicates, extract archives, mutate assets, launch DCC tools, submit ComfyUI
prompts, render, simulate, generate, or export. It writes a manifest/report
only.

Public package readiness is blocked if any package artifact contains a local
path marker. Oversized or missing artifacts are reported as package repair
blockers.

## Validation

```bash
make creative-production-hardening-check
```
