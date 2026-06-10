# Houdini Hython Smoke Runner v1 Runbook

## Purpose

Use SEOS to run a minimal local Houdini `hython` smoke only when Houdini is
available and the operator explicitly approves the process launch. The runner
writes one small JSON output file, hashes it, and records a materialization
record. If Houdini is missing or licensing blocks startup, the runner returns
truthful unavailable or license-blocked evidence instead of claiming success.

SideFX documents `hython` as Houdini's command-line Python shell, and command
line scripting may require a Houdini Batch or FX license. SEOS therefore treats
license failures as expected local-state evidence, not as hidden success.

## Default Unavailable Check

This check does not require Houdini and is safe for default validation:

```bash
make creative-houdini-runner-check
```

It writes deterministic unavailable evidence to:

- `reports/creative/houdini/hython_smoke_unavailable_v1.json`
- `reports/creative/houdini/hython_smoke_materialization_v1.json`

## Real Local Smoke

On a machine with Houdini installed, run:

```bash
python3 seos.py creative houdini-smoke \
  --mode public \
  --output-root work/creative_runs/houdini_smoke \
  --approve-local-execution \
  --approval-id approval-houdini-smoke-local-001 \
  --result-json reports/creative/houdini/hython_smoke_result.local.json \
  --materialization-json reports/creative/houdini/hython_smoke_materialization.local.json
```

If `hython` is not on PATH, set an explicit path:

```bash
SEOS_HYTHON_PATH=/path/to/hython \
python3 seos.py creative houdini-smoke \
  --mode local \
  --output-root work/creative_runs/houdini_smoke \
  --approve-local-execution \
  --approval-id approval-houdini-smoke-local-001
```

You can also pass `--hython /path/to/hython`. When supplied, `--hython` is
authoritative and does not silently fall back to another installed Houdini.

## Status Values

- `ENV_NOT_FOUND`: `hython` was not found; no process was launched.
- `USER_APPROVAL_REQUIRED`: `hython` was found but the operator did not approve
  execution; no process was launched.
- `EXECUTED`: the fixed SEOS smoke driver ran and materialized the output JSON.
- `LICENSE_BLOCKED`: `hython` returned a license or hserver-style failure.
- `LONG_TASK_BLOCKED`: the bounded timeout fired and the process was terminated.
- `EXECUTION_FAILED`: `hython` ran but did not produce valid smoke output.

## Safety Boundary

The runner:

- never accepts a raw command line or arbitrary argv from the user;
- launches only the detected or explicitly supplied `hython` executable;
- writes output only under the configured output root;
- refuses to overwrite an existing smoke output file;
- strips secret-like environment variables from the child process;
- uses `shell=False`;
- stores raw stdout/stderr only in `--mode local`; public mode stores hashes;
- does not require Houdini in default CI.

## Validation

```bash
make creative-houdini-runner-check
python3 scripts/creative_houdini_hython_smoke_v1.py \
  --hython tests/fixtures/creative/software_discovery/missing_hython \
  --output-root work/creative_runs/houdini_unavailable \
  --observed-at 2026-06-08T00:00:00Z \
  --result-json reports/creative/houdini/hython_smoke_unavailable_v1.json \
  --materialization-json reports/creative/houdini/hython_smoke_materialization_v1.json
git diff --check
```
