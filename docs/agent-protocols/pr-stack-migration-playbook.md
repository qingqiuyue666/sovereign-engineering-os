# PR Stack Migration Playbook

## Purpose

Capture the PR stack lesson from the #570, #574, #572, and #573 sequence so
future agents do not lose work, duplicate diffs, or cross merge gates.

## Lessons

## Stacked PR Squash Merge Risk

Squash merging a lower PR can make upper PRs appear dirty because their commit
history no longer matches `main`, even when content has landed. Treat the
branch diff against current `main` as the source of truth.

## Do Not Delete Branches Still Used by Upper PRs

Branches that support upper PRs are working evidence and recovery anchors. Do
not delete them while dependent PRs, replacement PRs, or review references still
exist.

## Replacement PR Pattern

When an original stacked PR becomes unusable or closes, create a replacement
branch from current `main`, reapply only PR-owned changes, open a replacement
draft PR, and link the original PR in the body for history.

## Retarget to Main After Lower PR Merges

After the lower PR merges, retarget or recreate the upper PR against `main`.
Then verify the diff contains only upper-layer work.

## Reconcile DIRTY Branch Against Current Main

For a dirty branch, compare against current `main`, identify duplicate
lower-stack changes, remove duplicates, and preserve only branch-owned changes.

## Preserve PR-Owned Changes

Before cleanup, list files and commits that belong to the PR. Do not discard
them while removing lower-stack duplicates.

## Remove Duplicate Lower-Stack Changes

If lower-stack files already exist on `main`, remove those duplicate diffs from
the upper branch instead of reintroducing them.

## Run Checks and Wait for CI

After reconciliation, run local checks, push the replacement or cleaned branch,
and wait for GitHub checks. Report pending or failing CI directly.

## Stop at Human Merge Gate

Opening or repairing a PR is agent-executable when requested. Final merge is a
human gate unless explicit authorization is provided.
