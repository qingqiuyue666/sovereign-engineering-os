# Branch Audit Report Workflow

## Purpose

The Branch Audit Report workflow gives the private operator a deterministic review packet for implementation branches before merge. It is a report builder only.

## Caller-Provided Material Only

This workflow uses caller-provided material only. The caller supplies repository URL, branch names, commit identifiers, changed file lists, verification summaries, risk notes, boundary findings, forbidden changes, merge blockers, the recommended action, and rollback plan.

## Execution Boundary

It does not run git or tests internally. It does not inspect GitHub, does not execute commands, does not access environment values, does not read secrets, and does not call providers.

## Inputs

- Report ID.
- Repository URL.
- Base branch and feature branch.
- Base commit and head commit.
- Changed, added, modified, and deleted files.
- Test matrix.
- Risk matrix.
- Boundary findings.
- Forbidden changes.
- Merge blockers.
- Recommended action.
- Rollback plan.
- Policy version.
- Code version.

## Markdown Output

The Markdown report renders these sections in deterministic order:

1. Executive Summary
2. Branch State
3. Changed Files
4. Test Matrix
5. Risk Matrix
6. Boundary Findings
7. Forbidden Changes
8. Merge Blockers
9. Recommended Action
10. Rollback Plan

## Failure Handling

Missing required material, invalid recommended actions, forbidden raw or sensitive field names, invalid digest fields, caller-supplied content hashes, or non-serializable material fail closed.
