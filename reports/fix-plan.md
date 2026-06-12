# Fix Plan

## Purpose

Separate safe fixes already applied from risky or evidence-dependent fixes
that should not be forced in this pass.

## Safe Fixes Applied

- Added root SEIS navigation and required root files.
- Added all required engine directories and README files.
- Added migration, validation, audit, gap, fix, and checkpoint reports.
- Archived previous README and ROADMAP before replacing them.
- Preserved existing runtime and untracked production-spine work.
- Ignored two generated large production-spine JSON outputs so creative
  validation passes without deleting local artifacts.

## Deferred Fixes

| Fix | Why Deferred | Next Step |
| --- | --- | --- |
| Deprecate large `docs/decisions/` tree file-by-file | Risk of breaking historical references | Create cleanup branch after validation |
| Convert protocol placeholders to schemas | Requires repeated delivery evidence | Wait for two accepted deliveries |
| Build credit/clearing runtime | Premature and high risk | Keep as placeholder |
| Add live provider integrations | Forbidden by current boundaries | Require explicit approval and safety design |
| Market proof claims | Requires external buyer evidence | Run first-wedge discovery |
| Full `make ci` | Current pass intentionally leaves a dirty worktree and `make ci` includes diff checking | Run after review/staging or in clean CI |

## Approval Needed

No approval is needed for the safe documentation fixes already applied.
Future cleanup that moves or deletes legacy files requires explicit user
approval.

## Upgrade Path

Re-run this plan after first paid signal and after repository validation.
