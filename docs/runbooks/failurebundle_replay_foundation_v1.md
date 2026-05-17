# Failure Bundle & Replay Foundation (V12-06)

## Overview
Provides sanitized failure bundle generation, deterministic replay plan descriptors, and replay diff comparison for exact replay verification.

## Components

### Failure Bundle (`kernel/runtime/failure_bundle.py`)
- `build_failure_bundle()` — deterministic sanitized failure descriptor
- `validate_failure_bundle()` — pure validation against policy
- No raw secrets, prompts, or provider responses stored

### Replay Plan (`kernel/runtime/replay_plan.py`)
- `validate_replay_plan()` — exact replay only, no cloud re-query
- Rejects `provider_live_requery=true`

### Replay Diff (`kernel/runtime/replay_diff.py`)
- `validate_replay_diff()` — compares expected vs actual output digests
- Reports `replay_match` true/false

## Local Verification
```bash
make test-failure-bundle
make test-replay-plan
make test-replay-diff
make test-failurebundle-replay-foundation
```

## Constraints
- No provider calls, no network, no SQLite, no file mutation
- All functions deterministic and side-effect free
- No production autonomy
