# AI Worker Result Review Packet Workflow

## Purpose

The AI Worker Result Review Packet workflow creates a deterministic structure-only packet for reviewing an AI worker final report.

## Claims Are Not Trusted

Worker claims are not trusted. The packet validates section structure, records claimed branch and commit, records claimed tests and results, and highlights missing sections or contradictions. It does not execute verification and does not prove the worker claims are true.

## Required Worker Final Report Sections

- FINAL_COMMIT
- BRANCH
- FILES_CHANGED
- TESTS_ADDED
- COMMANDS_RUN
- EXACT_RESULTS
- BOUNDARIES_PRESERVED
- DETERMINISM_AUDIT
- FAILURE_PATH_AUDIT
- ROOT_INTEGRITY_AUDIT
- REMAINING_RISKS
- ROLLBACK_PLAN

## Review Decisions

Allowed decisions are structurally_complete, structurally_incomplete, requires_human_verification, and reject. Missing required sections or contradiction findings block structurally_complete.

## Markdown Output

1. Worker Result Summary
2. Claimed Branch / Commit
3. Claimed Files Changed
4. Claimed Tests Run
5. Claimed Results
6. Boundary Claims
7. Missing Sections
8. Contradiction Findings
9. Review Decision
10. Required Human Checks
11. Claimed Rollback Plan

## Safety Boundary

The packet stores summarized claims only. It must not persist raw prompts, raw provider responses, raw exception dumps, raw traceback dumps, secrets, credentials, tokens, keys, passwords, or authorization material.
