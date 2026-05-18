# Merge Readiness Report Workflow

## Purpose

The Merge Readiness Report workflow is a deterministic private gate report for deciding whether a branch is ready to merge.

## Not A Merge Executor

This is not a merge executor. It does not merge branches, does not run git, does not run tests, does not inspect GitHub, and does not execute external actions. It only renders caller-provided verification material.

## Required Evidence

- Source and target branch.
- Source and target commit.
- Changed files.
- Protected files status for Makefile, root README, root integrity manifests, health gate wiring, governance files, and schema files.
- Test matrix.
- Clean tree status.
- Diff check status.
- Root integrity status.
- Blocked capability status.
- Merge decision.
- Merge blockers.
- Rollback plan.

## Decision Boundary

Allowed decisions are approved_for_merge, blocked, needs_human_review, and rejected. A protected file mutation marked unsafe blocks approved_for_merge. Any blocked capability violation blocks approved_for_merge.

## Markdown Output

1. Merge Readiness Summary
2. Branch Pair
3. Changed Files
4. Protected Files Status
5. Verification Matrix
6. Clean Tree / Diff Check
7. Root Integrity Status
8. Blocked Capability Status
9. Merge Decision
10. Merge Blockers
11. Rollback Plan

## Safety Boundary

No live provider calls, no network execution, no process launching, no environment value access, no SQLite, no production autonomy, no financial execution, and no trading automation.
