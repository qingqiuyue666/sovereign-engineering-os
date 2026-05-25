# Capability Token Lifecycle V1

## Scope

Capability Token Lifecycle V1 adds a standalone token lifecycle model for
future controlled local-runner actions. It binds a single-use capability token
to one command ID, one scope, one approval artifact, one repository revision,
and one expiry window.

## Dependency Status

This milestone has a semantic dependency on Real Local Runner Boundary V1, but
the implementation does not import or depend on unmerged runner code. Runner
integration remains deferred until the runner boundary is merged.

## Lifecycle

The lifecycle supports:

- issue
- consume
- revoke
- expiry rejection
- double-consume rejection
- wrong command ID rejection
- wrong scope rejection
- wrong repository revision rejection
- wrong approval artifact rejection
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

## Audit Receipts

Every issue, consume, revoke, and rejection path returns a deterministic
receipt. Receipt hashes exclude observation time so repeated validation of
the same event material remains stable.

## Merge Readiness

This branch can be reviewed independently as a contract model. Any runtime
integration with the real local runner must wait for the runner boundary PR to
merge and must keep command resolution inside the runner allowlist.
