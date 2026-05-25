# Capability Token Lifecycle V1

## Scope

Capability Token Lifecycle V1 adds a standalone token lifecycle model for
future controlled local-runner actions. It binds a single-use capability token
to one command ID, one run ID, one scope, one approval artifact, one repository
revision, the merged Real Local Runner Boundary V1 policy ID, the executable
resolution policy ID, and one expiry window.

## Dependency Status

Real Local Runner Boundary V1 is merged in main. This milestone imports the
merged runner allowlist and executable resolution policy identifier so token
bindings match the runner contract. It still does not launch the runner, execute
commands, resolve executables, or grant runtime authority by itself.

## Lifecycle

The lifecycle supports:

- issue
- consume
- revoke
- expiry rejection
- double-consume rejection
- wrong command ID rejection
- wrong run ID rejection
- wrong scope rejection
- wrong repository revision rejection
- wrong approval artifact rejection
- wrong runner boundary policy rejection
- wrong executable resolution policy rejection
- issue nonce replay rejection
- consume nonce replay rejection
- deterministic audit receipt generation

## Boundary

This model does not execute commands. It does not grant arbitrary shell,
`shell=True`, arbitrary argv, arbitrary command-line input, network access,
browser access, provider API calls, credential storage, production autonomy,
or unbounded daemon/scheduler behavior.

The allowed command IDs are contract identifiers only:

- `focused_runner_chain_tests`
- `full_unittest_discover`
- `make_ci`
- `diff_check`

The runner policy binding is `real_local_runner_boundary_v1`. The executable
resolution policy binding is
`real_local_runner_system_brew_repo_executable_resolution_v1`. A token does not
authorize command lines, argv overrides, shell execution, browser/network
access, provider access, credentials, or production admission; it only records
bounded approval for a later caller to present to the already-bounded runner.

## Audit Receipts

Every issue, consume, revoke, and rejection path returns a deterministic
receipt. Receipt hashes exclude observation time so repeated validation of
the same event material remains stable.

## Merge Readiness

This branch can be reviewed independently as a contract model after the merged
runner boundary. Any future concrete integration must keep command resolution
inside the runner allowlist and executable resolution inside the runner boundary.
