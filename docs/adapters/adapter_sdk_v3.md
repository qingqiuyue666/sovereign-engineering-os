# Adapter SDK V3

Adapters implement detect, validate_environment, plan, dry_run, execute, collect_evidence, and build_report. Execution defaults to USER_APPROVAL_REQUIRED unless a safe staged-output gate is explicitly satisfied.

## Operating Boundary

- Local-first execution is the default.
- Private assets stay out of tracked public artifacts.
- Long render, simulation, generation, and DCC jobs require budget gates and default to dry-run plans.
- External adoption is recorded only from real verifiable URLs and real actors.

## Validation

Run `python3 scripts/creative_total_check_v3.py` and the narrower gate for this area before public release.

## Evidence

Evidence is repository-local, schema-backed, and fixture-backed unless a real external signal is explicitly recorded.

## Residual Risk

Live DCC installations, paid asset licenses, and real community adoption require human or external confirmation.
