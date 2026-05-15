# WAL Checkpoint Policy Foundation v1

## Verdict

`WAL_CHECKPOINT_POLICY_FOUNDATION_READY_FOR_LOCAL_TESTS`

This branch adds a planner-only WAL checkpoint policy foundation.

It does not execute checkpoint, does not run checkpoint pragmas, does not truncate WAL, does not open a live database, and does not mutate SQLite state.

## Implemented

- `kernel/stores/sqlite/wal_checkpoint_policy.py`
- `tests/tracer_bullet/test_wal_checkpoint_policy.py`

## Policy Record

The policy record includes:

- `policy_id`
- `max_wal_pages`
- `max_wal_bytes`
- `max_age_seconds`
- `trigger_on_snapshot`
- `manual_checkpoint_allowed`
- `truncate_allowed`
- `created_at`
- `version`

In this foundation branch, `truncate_allowed` must be false. Truncation remains outside scope.

## Observation Record

The observation record includes:

- `wal_pages`
- `wal_bytes`
- `age_seconds`
- `snapshot_creation_pending`
- `dirty_tail_detected`
- `mid_segment_corruption_detected`

The observation is passed in by the caller. The planner does not inspect a live database or WAL file.

## Planner Output

The planner emits:

- `checkpoint_required`
- `reason_codes`
- `recommended_mode`
- `requires_human_approval: true`
- `execution_allowed: false`
- `truncate_allowed: false`
- `database_opened: false`
- `pragma_wal_checkpoint_executed: false`
- `wal_truncate_executed: false`
- `sqlite_state_mutated: false`
- `mutating_checkpoint_executed: false`

## Reason Codes

The planner can emit:

- `wal_pages_threshold_reached`
- `wal_bytes_threshold_reached`
- `wal_age_threshold_reached`
- `snapshot_trigger_pending`
- `dirty_tail_requires_recovery_review`
- `mid_segment_corruption_requires_recovery_review`

## Non-Execution Boundary

This branch is planner-only.

It must not:

- open a SQLite database
- execute checkpoint
- truncate WAL
- mutate SQLite state
- create checkpoint audit records
- alter checkpoint configuration

## Required Local Verification Commands

```bash
python3 -m unittest tests.tracer_bullet.test_wal_checkpoint_policy -v
python3 -m unittest tests.tracer_bullet.test_wal_checkpoint_policy_audit -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. WAL checkpoint policy planner tests pass.
2. WAL checkpoint policy audit tests pass.
3. Full tracer-bullet tests pass.
4. `make ci` passes.
5. No checkpoint execution is introduced.
6. No WAL truncation is introduced.
7. No live SQLite mutation is introduced by the planner.
8. Worktree is clean.

## Next Step

After this branch merges, the next branch should be:

```text
wal_checkpoint_observation_collector_v1
```

That branch should collect WAL observation metadata without checkpoint execution or truncation.
