# Codex Done Criteria

## Done Means Evidence-Matched

Codex work is done only when the requested target state has matching evidence
or all remaining work is recorded as skipped, blocked, or human responsibility.

## Universal Done Criteria

- Current branch, remote, base, and worktree state were inspected.
- Existing repository authority and validation surfaces were inspected.
- Changes are scoped to the requested target.
- Material claims point to files, diffs, checks, commits, PR state, or source
  records.
- Unsupported stronger claims are downgraded or explicitly blocked.
- Risky actions are downgraded before stop.
- Unsafe local actions are skipped and recorded.
- Final report exists for non-trivial work.

## Documentation / Protocol Work

Done requires:

- `git diff --check`
- path and link sanity where practical
- no repository-local absolute path leaks in new files
- no unsupported production, external validation, customer, paid-signal,
  delivery, deployment, global maturity, or final-platform claims
- final report with changed files, checks, skipped checks, and limitations

## Code Work

Done requires the documentation/protocol criteria plus:

- narrow script or unit validation when a script is changed
- lint or compile check where available
- full or focused tests when the code touches shared behavior
- failure output recorded if a required command cannot run

## App Work

Done requires the code criteria plus:

- install/build when available and safe
- local start command when available and safe
- core route or page smoke check
- console/runtime error check when tooling exists
- README run instructions if the app surface changes

## Publish Work

Done requires:

- dedicated branch
- scoped commit
- push to remote branch
- draft PR when GitHub auth is available
- no merge to `main` without explicit human approval
- final report updated with PR URL when available

## Not Done

The work is not done if:

- completion is based only on agent narrative
- local checks are skipped without reason
- a stronger claim is made without matching evidence
- the next action requires human authority and is not recorded
- unrelated local work is staged silently
