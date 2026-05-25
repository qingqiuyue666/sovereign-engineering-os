# Minimal Controlled Execution Contract V1

This contract is a foundation for a future Minimal Controlled Execution Kernel.
It defines immutable request, policy, receipt, failure, snapshot, verifier, and
command registry shapes only.

It does not implement subprocess behavior, a runner, shell command execution,
CLI execution, network calls, provider calls, browser control, plugin
execution, DCC launch, ComfyUI launch, MCP execution, scheduler behavior, or
daemon behavior. It also does not implement a launcher, task graph execution,
auto re-execution, package installation, file deletion, asset mutation, or a
new dry-run abstraction layer.

## Command Registry

Registry entries are immutable command-id records. Execution payloads may refer
to a `command_id`; they must not supply `argv`, `cwd`, `env`, `path`,
`executable`, `timeout`, `command`, `command_line`, `shell`, network,
provider, browser, plugin, DCC, ComfyUI, or MCP fields.

The initial registry contains exactly:

- `git_status_short`: `["git", "status", "--short"]`
- `git_diff_check`: `["git", "diff", "--check"]`

`unittest_discover_tests` and `make_ci` are intentionally deferred because unit
tests and make targets execute repo-owned code. They require a later sandbox,
pinned target, and stricter verification phase.

## Contract Objects

`ExecutionCommandRegistryEntry` binds command IDs to immutable fixed argv,
command class, read-only expectation, allowed verifier, registry version,
policy fields, command semantics, and a deterministic `registry_entry_hash`.

`ExecutionRequest` carries request metadata and a `command_id` reference only.
Its allowed metadata includes request ID, task ID, run ID, command ID, approval
token ID, requested-at timestamp, requester, policy version, use case IDs,
snapshot ref, caller intent, and request hash. Its forbidden fields are
`argv`, `command`, `command_line`, `shell`, `cwd`, `env`, `executable`,
`path`, `timeout`, `network`, `provider`, `browser`, `plugin`, `dcc`,
`comfyui`, and `mcp`.

`ExecutionPolicyDecision` is a deterministic admission result. Unknown command
IDs are represented as `POLICY_REJECTED` with `UNKNOWN_COMMAND_ID`. Missing
human approval is represented as `POLICY_REJECTED` with `APPROVAL_MISSING`.
Deferred command IDs are represented as `POLICY_REJECTED` with
`DEFERRED_COMMAND_ID`. Policy decisions carry policy version, registry version,
registry hash, and forbidden-surface flags set false.

`ExecutionReceipt` records only digest and truncation metadata for stdout and
stderr. Raw stdout and stderr are not part of the receipt contract. In this
contract-only slice the receipt status must be `CONTRACT_ONLY_NOT_EXECUTED` and
`execution_performed=false`.

`ExecutionFailureBundle` records failure evidence and includes
`WAL_APPEND_FAILED` and `EXECUTION_NOT_ATTEMPTED` failure types. It must carry
`execution_performed=false`.

`ExecutionSnapshotRef` names `PRE` and `POST` snapshot references by hash and
must carry `execution_performed=false`.

`ExecutionVerifierInput` binds request, decision, registry entry, receipt, and
snapshot hashes for a future verifier and must carry
`execution_performed=false`.

## Non-Implementation Boundary

This PR is contract-only. It does not widen existing execution runtime modules
and does not add an execution entrypoint. A future implementation phase must
separately prove sandboxing, clean worktree checks, approval validation, WAL
append guarantees, snapshot capture, and receipt verification before any local
execution kernel can run commands.
