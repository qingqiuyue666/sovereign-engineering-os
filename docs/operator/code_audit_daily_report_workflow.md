# Code Audit Daily Report Workflow

## Purpose

The Code Audit Daily Report workflow turns the existing Code Audit Workbench into a repeatable private operator reporting routine. It is a deterministic reporting workflow, not a repository scanner, not a CI runner, and not a network client.

## Caller-Provided Material Only

This workflow uses caller-provided material only. The caller supplies repository URL, main commit, branch state, verification results, changed capabilities, risks, blocked capabilities, recommended next actions, and rollback notes.

## No Internal Test Execution

The workflow does not run tests internally. It records verification results supplied by the caller after the caller has run the appropriate commands.

## Inputs

- Daily report ID.
- Repository URL.
- Main commit.
- Branch state.
- Verification matrix.
- Changed capabilities.
- Risk matrix.
- Blocked capabilities.
- Recommended next actions.
- Rollback notes.
- Policy version.
- Code version.

## Output

The output is a private deterministic Markdown report for the operator. The report may include observation metadata, but observation metadata must never enter deterministic hashes.

## Safety Boundary

- No live provider calls.
- No network execution.
- No process launching.
- No environment value access.
- No SQLite mutation or introduction.
- No raw prompts.
- No raw provider responses.
- No raw exception dumps.
- No raw traceback dumps.
- No financial execution.
- No trading automation.

## Daily Use

1. Operator or worker runs approved verification commands outside this workflow.
2. Operator or worker captures summarized results without raw dumps.
3. Caller passes the summarized material into the deterministic builder.
4. Builder validates fields, rejects forbidden material, computes a deterministic content hash, and renders Markdown.
5. Human review decides whether to merge, continue, or roll back.

## Failure Handling

Missing required fields, forbidden field names, invalid digest fields, or non-serializable material fail closed. A failed report build is not partial success and must not be treated as verification.
