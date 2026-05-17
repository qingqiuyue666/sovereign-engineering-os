# Replay Engine Foundation v1

## Purpose
Bounded local-only replay engine foundation. Validates replay requests
without executing any replays.

## Boundaries
- no cloud re-query as exact replay
- no missing input snapshot
- no missing version tuple
- no nondeterministic replay claim
- no production mutation
- no actual replay execution in v1

## Required Fields
replay_anchor_id, input_snapshot_hash, policy_version,
code_version, environment_fingerprint, deterministic_mode,
no_cloud_requery

## Operations
1. validate_replay_request — structural validation
2. validate_replay_anchor_contract — anchor integrity
3. validate_replay_input_snapshot_contract — snapshot hash validation
4. validate_replay_version_tuple — version completeness
5. produce_replay_engine_receipt — full receipt production

## Scope
Contract-only. Does not execute any replays.
