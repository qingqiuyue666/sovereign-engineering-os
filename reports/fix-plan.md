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
- Hardened current-facing root naming so SEIS is the primary active system
  name and SEOS remains earlier-line or legacy/runtime context.
- Updated the identity boundary validation script for current SEIS README
  headings while preserving unsupported-claim checks for SEIS and SEOS
  language.
- Clarified that scaffold completion is not paid traction, market proof,
  external audit, app/product launch, SaaS readiness, or Stage 16 completion.
- Packaged the first wedge as a bounded readiness-audit transaction with
  buyer, budget, trigger, trust-gap, pricing, acceptance, rejection,
  discovery, outreach, delivery-scope, objection, and close/loss assets.

## Deferred Fixes

| Fix | Why Deferred | Next Step |
| --- | --- | --- |
| Deprecate large `docs/decisions/` tree file-by-file | Risk of breaking historical references | Create cleanup branch after validation |
| Convert protocol placeholders to schemas | Requires repeated delivery evidence | Wait for two accepted deliveries |
| Build credit/clearing runtime | Premature and high risk | Keep as placeholder |
| Add live provider integrations | Forbidden by current boundaries | Require explicit approval and safety design |
| Build internal app/workbench runtime | Premature for this pass | Specify after execution kits exist; implement only after safe approval |
| Launch product/SaaS | Evidence not present | Wait for paid delivery, repeated workflow patterns, and support readiness |
| Market proof claims | Requires external buyer evidence | Run first-wedge discovery |
| Validate first wedge with buyers | Requires outreach and discovery | Use `first-wedge/` pack and record outcomes in Milestone 4 validation logs |
| Full `make ci` | Current pass intentionally leaves a dirty worktree and `make ci` includes diff checking | Run after review/staging or in clean CI |

## Approval Needed

No approval is needed for the safe documentation fixes already applied.
Future cleanup that moves or deletes legacy files requires explicit user
approval.

## Upgrade Path

Re-run this plan after first paid signal and after repository validation.
