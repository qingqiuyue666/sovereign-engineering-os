# Rollback Runbook V1

External review required: yes.

This runbook defines safe rollback for readiness changes.

## Rollback Trigger

Rollback is allowed when a merged change breaks `make ci`, mutates protected
release evidence, invalidates the root manifest, weakens secret safety, or
creates unsupported public claims.

## Safe Rollback

1. Open a new rollback branch from current `origin/main`.
2. Revert only the faulty change with an auditable commit.
3. Keep unrelated user or operator work intact.
4. Do not force push and do not rewrite protected tags.
5. Run the validation gate before opening or merging the rollback PR.

The rollback boundary is no force push, no tag rewrite, and no hidden evidence
deletion.

## Validation

The rollback PR must run the failing command, `make verify`, `make ci`,
`git diff --check`, and `git status --short`. If a release-candidate tag
invariant was involved, also run `git rev-parse 'v0.1.0-rc3^{}'`.

## Evidence Preservation

The rollback must preserve the original failing CI link, failing command, and
corrective commit. It must not delete evidence to hide a regression.

## Boundary

Rollback is an engineering recovery action. It does not publish a release,
expand runtime authority, or replace independent review.
