# Sovereign Engineering OS

Sovereign Engineering OS (SEOS) is being refocused into a local-first AI/VFX
production assistant and controlled execution/evidence system. Its practical
job is to help an operator scan local assets, classify what exists, detect
broken or duplicated production inputs, plan shots, inspect local tool
availability, run approved local tools where available, and record useful
outputs or truthful failure reports.

SEOS still records task intent, approval state, dry-run execution receipts,
evidence traces, replay explanations, failure bundles, and release checks. Those
controls now serve the production workflow rather than replacing it.

Product boundary:

- SEOS is a local-first AI/VFX production assistant and controlled
  execution/evidence system.
- SEOS is not an operating-system sandbox and not an OS-level sandbox.
- SEOS is not uncontrolled RPA, desktop automation, or computer control.
- SEOS is not RPA.
- SEOS is not a computer-control framework.
- SEOS is not a cloud production platform.
- SEOS is not a commercial SaaS platform.
- SEOS is not externally certified.
- Host permissions, process isolation, credential custody, EDR, containers,
  VMs, and cloud controls remain outside the SEOS boundary.

## Current Status

The repository contains a large amount of historical governance and readiness
work. Active development should now be judged by real production usefulness:
asset scans, readable reports, adapter truthfulness, shot plans, local outputs,
hashes, materialization evidence, and actionable failure records.

The repository still preserves `REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE`
artifacts as historical evidence.

Historical validated facts recorded in the repository:

- `SYSTEM_LANDED`
- `REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE`
- `LOCAL_REAL_USE_VALIDATED`
- `APPROVAL_GATE_VALIDATED`
- `CLEAN_CLONE_VALIDATED`
- `NO_HARD_EVIDENCE_BLOCKER_RECORDED`

Release candidate `v0.1.0-rc3` is preserved as an audit checkpoint. External
recognition has not been confirmed, and external verification is still
required.

## What SEOS Solves

AI-assisted engineering often leaves a gap between a human request and a
reviewable engineering record. SEOS narrows that gap by making the governance
objects explicit:

- task contracts describe requested work without granting hidden authority
- approval and rejection receipts make human decisions inspectable
- dry-run execution receipts bind outcomes to policy, inputs, and code state
- evidence traces connect claims to artifacts and validation commands
- replay explanations state what can and cannot be reconstructed
- failure bundles preserve bounded, digest-oriented failure context

The design goal is not to let AI do more by default. The goal is to reduce
manual production work while keeping local engineering and creative workflows
reviewable, reproducible, and fail-closed.

## What SEOS Is Not

SEOS must not be interpreted as any of the following:

- an operating-system sandbox or isolation layer
- a filesystem permission system
- an EDR, VM, container, or secret custody system
- RPA, browser automation, desktop automation, or computer control
- a live-provider AI execution runtime
- not an autonomous AI executor
- not a secret manager
- a way for AI to patch files without human-gated proposal, approval, and
  validation
- a commercial SaaS or hosted production service
- proof that global recognition or external signoff has happened

## Install

Requirements:

- Python `>=3.13`
- `openpyxl>=3.1,<4`
- Git

Local editable install:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
seos --help
```

Without installing, the module entrypoint is available from the repository
root:

```bash
python3 -m apps.operator_cli.main --help
```

## Quickstart

Create a local workspace:

```bash
seos init --workspace .seos-workspace
seos status --workspace .seos-workspace --human
```

Create a governed task:

```bash
seos task create \
  --workspace .seos-workspace \
  --title "review local validation" \
  --objective "Run the local validation plan and record evidence"
```

Approve and dry-run the task:

```bash
seos approve TASK_ID --workspace .seos-workspace --reason "operator approved"
seos run TASK_ID --workspace .seos-workspace --dry-run
```

Inspect evidence and replay context:

```bash
seos evidence trace TASK_ID --workspace .seos-workspace
seos replay explain TASK_ID --workspace .seos-workspace
seos receipt list --workspace .seos-workspace
```

Generate deterministic AI-governance support artifacts without calling a live
provider:

```bash
seos ai bundle TASK_ID --workspace .seos-workspace
seos ai repo-map --workspace .seos-workspace
seos ai token-roi TASK_ID --workspace .seos-workspace
```

## SEOS Creative Pipeline

SEOS Creative Pipeline is a local-first AI/VFX/3D/video workflow control plane.
It tracks assets, shots, DCC adapters, AI generations, render jobs, approvals,
evidence, and replay across ComfyUI, Blender, Houdini, ZBrush, Unreal Engine,
DaVinci Resolve, and After Effects.

Fixture-backed creative quickstart:

```bash
python3 seos.py creative health --json
python3 seos.py creative scan-assets --json
python3 seos.py creative adapter list --json
python3 seos.py creative dashboard build --json
```

Real local asset-library scan:

```bash
ASSET_ROOT=./local_asset_library
python3 seos.py creative scan-assets \
  --root "$ASSET_ROOT" \
  --mode public \
  --output-json reports/creative/assets/local_asset_library.public.json \
  --output-md reports/creative/assets/local_asset_library.public.md
```

Use `--mode public` for sanitized artifacts that use relative asset references.
Use `--mode local` only for operator-local reports that may include local
absolute paths. The scan is read-only for the asset root and never moves,
renames, deletes, deduplicates, extracts archives, or executes DCC tools.

Search a generated registry:

```bash
python3 seos.py creative search-assets \
  --registry-json reports/creative/assets/local_asset_library.public.json \
  --query missing-texture-sets
```

Build a local production dashboard:

```bash
python3 seos.py creative production-dashboard \
  --registry-json reports/creative/assets/local_asset_library.public.json \
  --output-md reports/creative/assets/local_production_dashboard.md \
  --output-html reports/creative/assets/local_production_dashboard.html
```

Build a local tool-health dashboard:

```bash
python3 seos.py creative tool-health-dashboard \
  --mode public \
  --output-json reports/creative/tool_health/local_tool_health_dashboard.json \
  --output-md reports/creative/tool_health/local_tool_health_dashboard.md \
  --output-html reports/creative/tool_health/local_tool_health_dashboard.html
```

The tool-health dashboard reports Python, Python dependencies, Git, FFmpeg,
Houdini/hython, ComfyUI, Blender, After Effects, DaVinci Resolve, Unreal Engine,
and ZBrush availability without launching DCC or AI tools or requiring
proprietary tools in default CI.

Run an approved local Houdini/hython smoke when available:

```bash
python3 seos.py creative houdini-smoke \
  --mode public \
  --output-root work/creative_runs/houdini_smoke \
  --approve-local-execution \
  --approval-id approval-houdini-smoke-local-001 \
  --result-json reports/creative/houdini/hython_smoke_result.local.json \
  --materialization-json reports/creative/houdini/hython_smoke_materialization.local.json
```

Without Houdini, the same runner returns truthful `ENV_NOT_FOUND` evidence. If
Houdini licensing blocks startup, it returns `LICENSE_BLOCKED` evidence.

Run an approved local ComfyUI workflow smoke against a running loopback service:

```bash
python3 seos.py creative comfyui-smoke \
  --workflow-json tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json \
  --endpoint http://127.0.0.1:8188 \
  --output-root work/creative_runs/comfyui_smoke \
  --approve-local-execution \
  --approval-id approval-comfyui-smoke-local-001 \
  --result-json reports/creative/comfyui/comfyui_smoke_result.local.json \
  --materialization-json reports/creative/comfyui/comfyui_smoke_materialization.local.json
```

The default fixture is an API-format `EmptyImage` to `SaveImage` smoke that
does not require model downloads. If no workflow is available, the runner
returns `ENV_NOT_FOUND`; if local ComfyUI is not answering on loopback, it
returns `SERVICE_UNAVAILABLE`; if approval is missing, it does not post to
`/prompt`.

Build optional adapter contracts for the remaining creative tools:

```bash
python3 seos.py creative optional-adapter-contracts \
  --mode public \
  --output-json reports/creative/adapters/optional_adapter_contracts.json \
  --output-md reports/creative/adapters/optional_adapter_contracts.md
```

This reports Blender, After Effects, DaVinci Resolve, Unreal Engine, and ZBrush
contract readiness without launching those tools or claiming execution support.

Build a practical shot plan from scanned assets:

```bash
python3 seos.py creative shot plan \
  --template energy-impact \
  --shot-id SHOT_ENERGY_IMPACT_001 \
  --registry-json reports/creative/assets/asset_library_report_v1.json \
  --output-json reports/creative/shots/shot_plan_energy_impact.json \
  --output-md reports/creative/shots/shot_plan_energy_impact.md
```

Shot templates report available candidates, missing required assets, manual
steps, and optional approval-gated runner commands without rendering or
launching creative tools.

The creative pipeline defaults to read-only scans, dry-run adapter plans,
fixture demos, and public/private separation. Real DCC execution, paid assets,
and external adoption signals require real local evidence or verified external
URLs; this repository does not claim external adoption.

## Validation

Baseline validation:

```bash
python3 scripts/observation_check_v1.py
python3 scripts/identity_boundary_check_v1.py
python3 scripts/creative_total_check_v3.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_identity_boundary_v1
make ci
```

`make ci` runs the canonical local health gate. It includes unit and acceptance
tests plus a diff check that requires a clean worktree.

## Observation Mode

Observation mode is a no-expansion posture. It allows evidence, documentation,
tests, audit reports, and narrow validation checks that improve external
reviewability. It does not authorize feature expansion, uncontrolled runtime
execution, live provider execution, browser control, OS automation, or
unapproved patching.

The observation record is maintained in:

- `docs/runbooks/real_operation_observation_period_v1.md`
- `reports/observation/real_operation_observation_log_v1.md`
- `reports/observation/real_operation_observation_log_v1.json`
- `governance/policy/observation_period_change_policy_v1.md`

## Evidence Model

Major claims should map to evidence:

`claim -> risk -> control -> implementation -> validation command -> CI or script gate -> evidence artifact -> residual risk`

Wave 1 public identity evidence is documented in:

- `docs/identity/system_identity_v1.md`
- `docs/identity/non_goals_v1.md`
- `docs/quickstart/local_first_quickstart_v1.md`
- `docs/architecture/seos_control_plane_v1.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `examples/README.md`

## Security Boundary

SEOS governs engineering workflow evidence. It does not reduce the authority of
the host process and does not custody secrets. Operators must avoid placing
secrets in task objectives, context bundles, receipts, examples, reports, or
issue comments. Live AI providers remain disabled by default and must not be
used to bypass proposal-first and human-approval requirements.

Report suspected security issues with digest-only evidence. Do not paste real
secrets, access tokens, private keys, `.env` contents, browser cookies, or
credential-store values into an issue, PR, receipt, report, or model context.

## Known Limitations

- External audit has not yet been performed.
- Global recognition is not confirmed.
- Real-world 30-90 day operation evidence is still required before any stronger
  recognition claim.
- The CLI supports local governance flows; it is not a remote service or
  automation platform.
- Replay explanation is bounded by recorded evidence and must not claim
  reconstruction when required evidence is missing.
- Live provider admission is not enabled by default.
- Host-level security controls remain the operator's responsibility.

## External Audit Readiness

This repository is being prepared for external engineering, security, SRE,
supply-chain, and AI-governance review. The strongest valid Codex-prepared
state is `GLOBAL_RECOGNITION_READINESS_READY_FOR_EXTERNAL_REVIEW`, which still
requires independent external verification and human audit.
