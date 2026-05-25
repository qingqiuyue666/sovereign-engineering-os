# Minimal Controlled Execution Admission WAL Verifier V1

This contract connects Minimal Controlled Execution Contract V1 to admission,
WAL-safe evidence, verifier binding, and replay manifest closure. It is still
contract-only.

It does not implement subprocess behavior, a runner, shell command execution,
CLI execution, network calls, provider calls, browser control, plugin
execution, DCC launch, ComfyUI launch, MCP execution, scheduler behavior, or
daemon behavior. It also does not add task graph execution, auto re-execution,
or any command execution path.

## Integration Flow

`ExecutionRequest` remains the request boundary from the source contract. The
admission layer accepts a request that references only a `command_id`; it does
not accept request-supplied `argv`, `cwd`, `env`, `path`, `executable`,
`timeout`, `command`, `command_line`, `shell`, network, provider, browser,
plugin, DCC, ComfyUI, or MCP fields.

`ExecutionAdmissionRecord` binds request identity, request hash, registry entry
hash, registry hash, policy version, registry version, acceptance state,
rejection reasons, approval token ID, and `execution_performed=false`.
Known command IDs in the v1 registry can be admitted. Unknown command IDs and
deferred command IDs are deterministically rejected.

`ExecutionWalRecord` records append-only, WAL-safe evidence for admission,
rejection, failure bundle creation, verifier input creation, and explicit
not-attempted evidence. It stores only hashes and metadata. It does not contain
raw stdout, raw stderr, command lines, argv, or execution output.

`ExecutionVerifierBinding` binds request, decision, admission, registry,
snapshot, receipt, and failure references for verifier input. It cannot claim
execution success and must carry `execution_performed=false`.

`ExecutionReplayEvidenceManifest` closes the contract-only replay evidence for
accepted-not-executed, rejected-not-executed, and failure-not-executed states.
Its WAL hashes are ordered and non-empty. It stores no raw output and no command
material.

## Registry Boundary

The v1 registry remains exactly:

- `git_status_short`
- `git_diff_check`

`unittest_discover_tests` and `make_ci` remain deferred. They are not admitted
by this contract because they execute repo-owned code and require a later
sandboxed implementation phase.

## Contract Objects

`ExecutionAdmissionRecord` represents deterministic admission of an
`ExecutionRequest` into governance flow. It must bind request hash, registry
entry hash, registry hash, policy version, registry version, acceptance state,
rejection reasons, approval token ID, and admission hash.

`ExecutionWalRecord` represents WAL-safe evidence. Allowed record types are
`EXECUTION_ADMISSION_ACCEPTED`, `EXECUTION_ADMISSION_REJECTED`,
`EXECUTION_FAILURE_BUNDLE_CREATED`, `EXECUTION_VERIFIER_INPUT_CREATED`, and
`EXECUTION_NOT_ATTEMPTED`. The sequence must be an integer greater than zero.

`ExecutionVerifierBinding` represents deterministic verifier binding for the
contract-only evidence chain. It binds request, decision, admission, receipt or
failure, pre-snapshot, post-snapshot, registry entry, and registry hashes.

`ExecutionReplayEvidenceManifest` represents replay evidence closure. Allowed
manifest statuses are `CONTRACT_ONLY_ACCEPTED_NOT_EXECUTED`,
`CONTRACT_ONLY_REJECTED_NOT_EXECUTED`, and
`CONTRACT_ONLY_FAILURE_NOT_EXECUTED`.

## Non-Implementation Boundary

This PR does not widen the registry, does not add a runner, and does not add a
CLI or scheduler. `execution_performed` remains false across all new
integration objects.
