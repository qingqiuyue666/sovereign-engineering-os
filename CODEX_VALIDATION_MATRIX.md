# Codex Validation Matrix

## Purpose

Define the minimum validation required before Codex claims a repository target
is complete, partial, or blocked.

## Validation Levels

| Level | Evidence type | Proves | Does not prove |
| --- | --- | --- | --- |
| L0 | Agent narrative | Intent only | Completion |
| L1 | Local command output | Local check result in this checkout | CI, merge, deployment, external validation |
| L2 | Git diff or commit | Repository change exists | Review acceptance or runtime operation |
| L3 | CI / GitHub checks | Remote engineering check result | Production or customer validation |
| L4 | Human review / acceptance | Human approval for the scoped repository action | Market proof |
| L5 | Real-world source records | External validation, paid signal, delivery, or operation evidence | Anything outside recorded scope |

## Documentation / Protocol Changes

Required:

```bash
python3 scripts/codex_execution_system_check_v1.py
git diff --check
```

Recommended when touched content overlaps existing boundaries:

```bash
python3 scripts/identity_boundary_check_v1.py
python3 scripts/claim_to_evidence_check_v1.py
python3 scripts/secret_context_safety_check_v1.py
python3 scripts/aoos_stage45_check_v1.py
```

Manual review:

- markdown consistency review
- link/path sanity where practical
- claim-language scan for unsupported stronger claims

## Code Changes

Required when code changes:

- focused script execution or unit test
- compile check where practical
- lint if a lint target exists
- smoke test if the changed behavior has a smoke target

## App Changes

Required when app surfaces change:

- install/build if possible
- local start command if possible
- route/page smoke check
- runtime/console error check if tooling exists
- README or run instruction update if commands changed

## Checks That Cannot Run

If a check cannot run, record:

- command
- reason
- missing dependency or permission
- impact on target state
- owner of remaining action
- whether the target is `ACHIEVED`, `PARTIAL`, or `BLOCKED`

## Minimum Final Validation For This System

The internal execution-system target requires:

```bash
python3 scripts/codex_execution_system_check_v1.py
python3 -m py_compile scripts/codex_execution_system_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_codex_execution_system_check_v1 -v
make codex-execution-system-check
git diff --check
```

CI should be reported after the draft PR is pushed. If CI is pending or
unavailable, the final report must say so directly.

## Eleven-Layer Evidence Pack

`ELEVEN_CORE_DELIVERY_LAYERS_V1_READY` also requires the source freshness audit,
frontier gap search audit, external project absorption shortlist, real task
throughput ledger, runtime state ledger, table-review residue closure,
real-world proof gap ledger, 100-point maturity ladder, continuous maturity
iteration queue, whole-content completion checklist, final report, and scorecard
to pass `scripts/codex_execution_system_check_v1.py`.
