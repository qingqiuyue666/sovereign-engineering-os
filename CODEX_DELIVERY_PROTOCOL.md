# Codex Delivery Protocol

## Purpose

Define how Codex publishes repository work without merging, deploying, or
claiming stronger evidence than the branch proves.

## Required Delivery Fields

Every non-trivial final report must include:

- target state
- final status: `ACHIEVED`, `PARTIAL`, or `BLOCKED`
- branch name
- base branch
- commit SHA or the exact reason no commit exists
- PR link if opened
- changed files
- checks run
- checks skipped and why
- skipped-risk register update
- blocked items
- remaining human-responsibility items
- explicit non-claim statement

## Branch Rules

- Use a dedicated branch for scoped work.
- Do not push directly to `main`.
- Do not merge; this is the no merge default.
- If the current branch is stale or already merged, create a new branch from
  current `origin/main`.

## Commit Rules

- Stage only intended files.
- Preserve unrelated untracked files.
- Use a terse commit message.
- If the final report needs the PR URL, open the draft PR after the first
  commit, then update the report in a follow-up commit.

## Draft PR Rules

- Open a draft PR by default.
- Base it on `main` unless a stacked review boundary is safer and explicitly
  recorded.
- PR body must include what changed, why, checks run, skipped checks, skipped
  risks, and the non-claim statement.
- Do not retarget after opening if that changes the review boundary without
  human approval.

## Final Chat Response

The final chat response must report only:

- final status
- branch
- commit SHA
- PR link
- files created
- files modified
- checks run
- checks skipped and why
- skipped or blocked items
- whether `END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY` is achieved
- for `ELEVEN_CORE_DELIVERY_LAYERS_V1_READY`, the source intake summary,
  frontier gap search summary, external absorption decisions, Run 01 result,
  second safe micro-task result, maturity verdicts, whole-content checklist
  result, and explicit non-claim statement
