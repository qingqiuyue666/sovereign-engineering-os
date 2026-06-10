# Interrupted Run Policy V1

External review required: yes.

This policy covers interrupted readiness runs, tool restarts, and resumed
work.

## Interrupted Run

An interrupted run is any wave where command output, CI status, or merge state
cannot be trusted from memory alone. The next action is to inspect repository
state and GitHub state before editing or merging.

## Resume

Resume from the latest `origin/main` state or the active wave branch after
checking `git status --short`, current branch, current HEAD, and the release
candidate tag invariant. If the branch already exists, continue on it only
after confirming it is clean or understanding each change.

## Idempotent Action

Repeated validators and benchmark commands must be idempotent. They may create
temporary files that are cleaned by the command, but they must not rewrite
tracked evidence unless the wave explicitly updates that evidence.

## Evidence

Evidence after resume must come from commands, files, PR status, or CI status.
Do not invent missing evidence, missing approval, or missing validation
results.

## Stop Condition

If the same blocking condition repeats and no safe progress remains possible,
stop with the human-decision blocker required by the readiness program.
