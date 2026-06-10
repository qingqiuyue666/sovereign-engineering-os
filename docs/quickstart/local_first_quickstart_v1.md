# Local-First Quickstart V1

## Purpose

This quickstart gives an external reviewer a minimal local path to inspect SEOS
without private chat context.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
seos --help
python3 -m apps.operator_cli.main --help
```

## Create A Workspace

```bash
seos init --workspace .seos-workspace
seos status --workspace .seos-workspace --human
```

## Create And Govern A Task

```bash
seos task create \
  --workspace .seos-workspace \
  --title "local validation review" \
  --objective "Run local validation and record evidence"
```

Use the returned task id in the next commands:

```bash
seos approve TASK_ID --workspace .seos-workspace --reason "operator approved"
seos run TASK_ID --workspace .seos-workspace --dry-run
```

## Inspect Evidence

```bash
seos evidence trace TASK_ID --workspace .seos-workspace
seos receipt list --workspace .seos-workspace
seos replay explain TASK_ID --workspace .seos-workspace
seos failure explain TASK_ID --workspace .seos-workspace
```

## Validate Repository State

```bash
python3 scripts/observation_check_v1.py
python3 scripts/identity_boundary_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_identity_boundary_v1
make ci
```

## Safety Notes

- Do not use secrets in task objectives or approvals.
- Do not treat dry-run receipts as proof of real-world execution.
- Do not treat replay explanation as reconstruction unless evidence exists.
- Do not enable live providers by default.
- Do not treat SEOS as an OS sandbox, RPA, computer-control framework,
  autonomous AI executor, commercial SaaS platform, or secret manager.

## Evidence Chain

| Claim | Risk | Control | Implementation | Validation command | Gate | Evidence artifact | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A reviewer can start locally | Private chat context may be required | Local install and CLI commands | This quickstart | `seos --help` | packaging and CLI tests | README and quickstart | Python/tool versions can differ |
| Validation is explicit | Reviewers may trust prose only | Commands listed in one place | Validation section | `make ci` | CI and local health gate | command output | Long-running validation still requires local resources |
