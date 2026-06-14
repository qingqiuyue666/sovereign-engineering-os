# Failure Handling IF/THEN Playbook

## PR DIRTY

IF the PR branch contains duplicate lower-stack changes, stale commits, or
unexpected drift, THEN compare against current `main`, identify PR-owned
changes, remove lower-stack duplicates, preserve intended branch changes, and
rerun checks before pushing.

## CI Failed

IF CI fails, THEN read the failing job, classify whether the failure was caused
by this branch, apply one narrow safe fix when the cause is in scope, rerun
local checks, push the fix, and wait for CI again. If still failing, stop with a
blocker report.

## Stale Metadata

IF status docs, PR bodies, branch names, or checkpoint metadata refer to a
closed, replaced, or merged lower PR, THEN update only the affected references
to current state. Do not rewrite unrelated strategy or claim stronger evidence.

## Broken Path Reference

IF a new or changed document references a path that does not exist, THEN either
create the required path when it is in scope or correct the reference to the
existing artifact. Rerun checks that scan docs.

## Duplicate Lower-Stack Diff

IF an upper branch still includes changes already merged through a lower PR,
THEN retarget or rebase only when safe, or make a replacement branch from
current `main` and reapply only PR-owned changes. Do not delete branches still
used by open PRs.

## Branch Deleted

IF a branch used by an open PR is deleted or unavailable, THEN stop destructive
recovery, create a replacement branch from the correct base, reapply PR-owned
changes from commits or diffs, open a replacement draft PR, and link the old PR
history in the new PR body.

## Untracked Preserved Files

IF preserved untracked files are present, THEN do not stage, delete, or hide
them unless explicitly requested. Use explicit `git add` paths for the intended
branch changes and report the preserved untracked files as worktree context.

## Still Blocked After Retry

IF a required check or publish step still fails after one narrow retry, THEN
stop. Report the command, failure output summary, attempted fix, remaining
risk, and the exact human decision needed.
