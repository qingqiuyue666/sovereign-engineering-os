# Codex CI Reality Gate

## Gate

Separate local checks, GitHub Actions checks, skipped checks, unavailable
checks, and branch-protection evidence. A local pass is not a CI pass.

## Evidence Path

- `reports/checkpoints/eleven-core-delivery-layers-v1-final-report.md`
- GitHub PR checks
- `reports/checkpoints/runtime-state-ledger-v1.md`
- Branch-protection API attempt returned HTTP 403 in this run, so required
  branch-protection evidence is unavailable.

## Non-Claim Boundary

CI required checks / branch protection is `PARTIAL` unless GitHub Actions and
required-check/branch-protection evidence exists.
