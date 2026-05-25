# Mainline Release Readiness Gate V1

## Scope Summary

Mainline Release Readiness Gate V1 defines the evidence required before a
human may consider mainline milestone closure for Sovereign Engineering OS.
It is a repository-owned contract and recommendation artifact format, not a
release mechanism.

## Descriptor Files

- `governance/release/mainline_release_readiness_gate_v1.json`
- `governance/release/mainline_release_recommendation_artifact_v1.json`

## Required Evidence

Each candidate milestone must provide:

- open PR URL and branch name
- head SHA and changed file list
- focused test result
- `python3 -m unittest discover tests` result
- `make ci` result
- `git diff --check` result
- GitHub Actions run URL and passing status
- dependency notes and independent mergeability status
- forbidden-surface confirmation

The descriptor records milestone-specific evidence for delivery control,
local runner boundary, token lifecycle, job queue, replay, evidence
visibility, worker registry, adapter foundation, acceptance, and release
readiness.

## Validation Commands

The mainline readiness gate requires the following validation commands before
any positive release recommendation can be produced:

- `python3 -m unittest discover tests`
- `make ci`
- `git diff --check`
- `git status --short`

The readiness contract treats missing, failed, or pending validation as a
negative or waiting recommendation. It does not skip tests and does not
weaken failing tests.

## Recommendation States

The only allowed recommendation states are:

- `RELEASE_ALLOWED`
- `DO_NOT_RELEASE`
- `WAITING_FOR_CI`
- `BLOCKED`

`RELEASE_ALLOWED` requires all milestone evidence, all required local
validation, passing GitHub Actions, a completed forbidden-surface scan, and
rollback/recovery evidence. Any missing release evidence remains
`DO_NOT_RELEASE`, any pending CI remains `WAITING_FOR_CI`, and any forbidden
surface remains `BLOCKED`.

## Rollback And Recovery Evidence

The gate requires a non-destructive rollback and recovery record before a
positive recommendation:

- rollback trigger
- rollback scope
- recovery entrypoint
- quarantine entrypoint
- evidence preservation plan
- operator review owner

The rollback and recovery evidence is a release-review requirement only. This
contract does not perform rollback, recovery, release, or production
promotion.

## Boundary Statement

This milestone is governance and static validation only. It authorizes no
runtime execution, no browser or network behavior, no provider API calls, no
credential storage, no production autonomy, no unbounded daemon or scheduler,
no source asset overwrite, no branch deletion, no push to main, no PR merge,
and no release automation.

## Review Readiness Criteria

The E2 PR is review-ready when:

- focused E2 validation passes
- `python3 -m unittest discover tests` passes
- `make ci` passes
- `git diff --check` passes
- GitHub Actions passes
- the PR body records the CI run URL and the release-readiness boundary

The PR may be reviewed independently because it introduces only static
release-readiness governance and tests.
