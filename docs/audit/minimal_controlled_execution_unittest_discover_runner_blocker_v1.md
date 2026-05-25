# Minimal Controlled Execution Unittest Discover Runner Blocker V1

## Decision

Status: BLOCKED_FOR_IMPLEMENTATION

This audit does not implement `unittest_discover_tests` as an executable
minimal controlled runner in this PR train. The implementation is possible, but
not safely reviewable without first changing the command registry contract,
admission expectations, static guards, timeout policy, and acceptance tests in a
single coordinated stack.

## Requested Command

- command id: `unittest_discover_tests`
- fixed argv: `["python3", "-m", "unittest", "discover", "tests"]`

## Exact Blockers

1. The current minimal controlled execution contract treats
   `unittest_discover_tests` as deferred. Making it executable requires moving
   it into `INITIAL_COMMAND_REGISTRY` and removing it from
   `DEFERRED_COMMAND_IDS`.

2. Existing contract, admission, runner, roadmap, and static guard tests pin the
   executable registry to exactly `git_status_short` and `git_diff_check`.
   Updating those expectations is a contract migration, not a small runner-only
   addition.

3. The repository unit test suite can take more than two minutes locally.
   `unittest_discover_tests` therefore needs an explicit fixed timeout policy
   that differs from the existing git check timeout, plus tests proving the
   timeout is fixed and cannot be payload-controlled.

4. The Python test command needs a deterministic environment decision. The git
   runners use the git-safe env. A unittest runner should likely add
   `PYTHONDONTWRITEBYTECODE=1`, but that env policy must be made explicit in
   the contract and tests.

5. A safe implementation needs verifier tests for timeout, nonzero exit, output
   truncation, tamper rejection, and raw-output exclusion before the command can
   be admitted as executable.

## Smallest Safe Implementation Path

1. Create a contract migration PR that adds `unittest_discover_tests` to the
   registry with fixed argv, fixed timeout, deterministic Python test env, and
   digest-only output metadata policy.

2. Update admission and static guard tests to permit exactly three executable
   command ids while keeping `make_ci` deferred.

3. Add `kernel/execution/minimal_controlled_unittest_discover_runner.py` using
   the narrow shared helper layer from the shared runner base stack. The module
   must keep its own executable allowlist exactly
   `{"unittest_discover_tests"}`.

4. Add focused tests for fixed argv, `shell=False`, env, timeout, payload
   override rejection, rejection of git commands and `make_ci`, timeout failure,
   nonzero failure, output truncation, verifier tamper rejection, and forbidden
   imports.

5. Only after focused tests pass, run full repository validation and open the
   implementation PR.

## Boundary Statement

This blocker PR adds no execution capability, no command registry change, no
subprocess surface, no CLI, no scheduler, no daemon, no broad runner
abstraction, no provider/browser/DCC/MCP surface, and no package installation
path.
