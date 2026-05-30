# Maintenance Policy V1

External review required: yes.

This policy governs routine maintenance during readiness work.

## Maintenance Window

Maintenance can occur in ordinary development time as long as it uses a branch,
PR review surface, and passing checks before merge. Emergency fixes follow the
incident response and rollback runbooks.

## Dependency Review

Dependency changes require a reason, bounded version range, installability
check, and supply-chain check. New dependencies must not introduce live
provider calls, secret custody, or network behavior by default.

## Validation Gate

Every maintenance change must run the relevant targeted validator plus
`make verify` and `make ci`. Documentation-only changes still need the static
checks that protect claims, paths, and root integrity.

## Change Record

The PR description must identify changed evidence, changed policy, validation
commands, and residual risk. The changelog should be updated when public
readiness evidence changes.

## External Review

Maintenance evidence is input for external review. It is not independent
certification and must not be described as final signoff.
