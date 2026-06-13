# PR Stack Migration v1

Operational checklist for reconciling stacked PRs after lower branches merge,
close, squash merge, or are replaced.

## Checklist

- Confirm repository root and remote.
- Fetch current remote state.
- Identify current branch, base branch, and PR number.
- Confirm lower PR merge or closure state.
- Confirm whether any branch still supports upper PRs.
- Do not delete branches still used by open or referenced PRs.
- Compare the PR branch against current `main`.
- List PR-owned files and commits before cleanup.
- Identify duplicate lower-stack changes already present on `main`.
- Remove duplicate lower-stack changes from the PR diff.
- Preserve PR-owned changes.
- Fix stale PR metadata and path references.
- Run local checks.
- Push the cleaned or replacement branch.
- Open or update a draft PR.
- Wait for CI or report CI status directly.
- Stop at the human merge gate.

## Replacement PR Pattern

Use a replacement PR when the original PR cannot be safely reconciled:

1. Create a new branch from current `main`.
2. Reapply only PR-owned changes.
3. Run local checks.
4. Push the replacement branch.
5. Open a draft PR.
6. Link the original PR and explain why replacement was required.
7. Stop before merge.

## Evidence to Record

- original PR
- replacement PR when applicable
- branch names
- commit hashes
- changed files
- checks and CI status
- removed duplicate lower-stack diff
- remaining human gate
