# Security Policy

SEOS is a local-first engineering governance control plane. It records task,
approval, evidence, replay, receipt, and validation artifacts. It is not an
OS-level sandbox, not RPA, not a computer-control framework, not an autonomous
AI executor, not a commercial SaaS platform, and not a secret manager.

## Supported Posture

Current repository posture:

- `SYSTEM_LANDED`
- `REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE`
- `LOCAL_REAL_USE_VALIDATED`
- `APPROVAL_GATE_VALIDATED`
- `CLEAN_CLONE_VALIDATED`
- `NO_HARD_EVIDENCE_BLOCKER_RECORDED`

Release candidate `v0.1.0-rc3` is an immutable audit checkpoint for this
program. It must not be moved, deleted, recreated, or retagged.

## Boundary

SEOS provides governance-level controls:

- task contracts
- human approval and rejection receipts
- dry-run execution receipts
- evidence traces
- replay explanations
- failure bundles
- release and observation checks

SEOS does not provide host isolation, kernel controls, filesystem permissions,
EDR, VM/container boundaries, credential custody, or browser/desktop/OS
automation. Operators must assume the running process keeps the privileges
granted by the host OS.

## Secret Safety

Do not put secrets into:

- task objectives
- task descriptors
- approvals or rejection reasons
- context bundles
- model prompts or outputs
- receipts
- evidence traces
- replay explanations
- issue or PR text
- audit reports

Do not read, print, copy, inspect, or exfiltrate `.env` files, SSH keys,
keychains, browser cookies, cloud credentials, API keys, private tokens, or
credential stores while preparing evidence. Use secret references and digest-only
evidence where a secret-dependent workflow must be discussed.

## Reporting A Security Issue

Report suspected issues with bounded, digest-only evidence. Include:

- affected file or component name
- observed behavior
- expected fail-closed behavior
- validation command, if safe to share
- redacted logs or hashes only
- residual risk if known

Do not include real credentials, token values, private keys, `.env` contents,
browser cookie values, or raw private data.

## AI Provider Boundary

Live providers are disabled by default. AI output must not directly patch the
repository. Provider admission requires proposal-first review, bounded context,
secret-ref-only handling, token-budget controls, response receipts, and human
approval before any patch is applied.

## Security Validation

Current Wave 1 validation:

```bash
python3 scripts/observation_check_v1.py
python3 scripts/identity_boundary_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_identity_boundary_v1
make ci
```

Failures must not be hidden. Do not print a passing result after a required
validation command fails.
