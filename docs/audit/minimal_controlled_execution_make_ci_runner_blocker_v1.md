# Minimal Controlled Execution Make CI Runner Blocker V1

## Decision

Status: BLOCKED_FOR_IMPLEMENTATION

This audit does not implement `make_ci` as an executable minimal controlled
runner. `make ci` is the broadest requested local execution surface in this
train and should not be admitted before the command registry migration,
unittest runner gate, and WAL adapter plan are resolved.

## Requested Command

- command id: `make_ci`
- fixed argv: `["make", "ci"]`

## Exact Blockers

1. `make_ci` is currently a deferred command id. Making it executable requires
   a contract migration that changes the registry and admission semantics.

2. `make ci` is a compound build target. Even with fixed argv, it delegates to
   Makefile contents and therefore carries more surface than a single git check
   or a direct unittest invocation.

3. The Phase 4 unittest runner is not yet safely implemented. `make ci`
   includes test execution and should not be admitted before the narrower
   unittest runner is admitted and verified.

4. The repository does not yet have a real minimal WAL adapter. A `make ci`
   runner should require append-before-execution evidence and post-execution
   receipt/failure/verifier evidence before it becomes executable.

5. A safe implementation needs explicit tests for timeout, nonzero exit, output
   truncation, raw-output exclusion, verifier tamper rejection, payload override
   rejection, forbidden imports, and proof that no package installation trigger
   is introduced beyond existing Makefile behavior.

## Smallest Safe Implementation Path

1. Land the unittest runner contract migration first.

2. Audit the current Makefile `ci` target and freeze the exact allowed command
   expansion expectations in tests. Any package installation, network, provider,
   browser, DCC, MCP, plugin, scheduler, or daemon surface must remain
   forbidden.

3. Add `make_ci` to the minimal registry with fixed argv, fixed timeout,
   deterministic env, digest-only bounded output metadata, and a runner-local
   executable allowlist exactly `{"make_ci"}`.

4. Add the runner only after a narrow WAL adapter path exists or explicitly
   document that the runner remains contract-evidence-only until that adapter is
   available.

5. Validate with focused tests, full unit discovery, `make ci`, and
   `git diff --check` from a clean worktree before opening an implementation PR.

## Boundary Statement

This blocker PR adds no execution capability, no command registry change, no
subprocess surface, no Makefile mutation, no package installation path, no CLI,
no scheduler, no daemon, no provider/browser/DCC/MCP surface, and no broad
runner abstraction.
