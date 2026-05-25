# Command Envelope Admission Router V1

## Decision

Add a command envelope admission router as the first physical execution safety
gate. The router accepts a small XML envelope, rejects forbidden payload fields,
and allows the payload to express only a `COMMAND_ID` intent. The command id is
resolved through a local immutable registry before any execution can occur.

## Physical spine contribution

The router is the physical blast valve for local command execution. Calling
`route_envelope(xml_string)` performs admission only. Optional subprocess use is
disabled by default and is available only through `route_envelope(...,
execute=True)`.

## Safety boundaries

- `STATUS` values are limited to `PASS`, `BLOCKED`, and `FATAL`.
- `BLOCKED` and `FATAL` always produce quarantine reports and never execute.
- `PASS` is not authorization by itself.
- Payloads cannot provide command text, argv, executable paths, cwd, env, path
  overrides, network hints, browser hints, provider hints, credentials, secrets,
  or file mutation paths.
- Execution, when explicitly requested, uses `subprocess.run` with `shell=False`
  and the registry-owned argv tuple only.

## Registry

Initial command ids are:

- `focused_replay_engine_test`
- `focused_external_pattern_test`
- `diff_check`

Each registry entry records argv hash, policy id, risk class, execution level,
timeout, cwd policy, environment policy id, approval requirement, and token
requirement.

## Non-goals

This does not enable production autonomy, provider access, browser automation,
network activity, credential storage, arbitrary argv, command-line execution, or
payload-directed filesystem mutation.
