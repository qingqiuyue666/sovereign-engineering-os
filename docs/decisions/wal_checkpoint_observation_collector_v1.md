# WAL Checkpoint Observation Collector v1

## Verdict

`WAL_CHECKPOINT_OBSERVATION_COLLECTOR_READY_FOR_LOCAL_TESTS`

This branch adds an observation-only WAL checkpoint metadata collector.

It does not execute checkpoint, does not truncate WAL, does not open write transactions, and does not mutate SQLite state.

## Implemented

- `kernel/stores/sqlite/wal_checkpoint_observation_collector.py`
- `tests/tracer_bullet/test_wal_checkpoint_observation_collector.py`

## Scope

The collector records:

- database path
- WAL path
- database file existence
- WAL file existence
- WAL file bytes
- page size
- estimated WAL pages
- WAL modification time
- observation time
- age seconds
- snapshot creation pending flag
- dirty-tail flag supplied by caller
- mid-segment-corruption flag supplied by caller
- planner-compatible observation payload

## Allowed Reads

The collector may read:

- filesystem metadata for the database and WAL path
- WAL file size
- WAL file modification time
- optional read-only SQLite `PRAGMA page_size;`

The page-size probe must use read-only database access and must not open a write transaction.

## Non-Execution Boundary

The collector must not:

- execute checkpoint
- truncate WAL
- mutate SQLite state
- open write transactions
- inspect WAL frames
- classify dirty tail by itself
- classify mid-segment corruption by itself
- create checkpoint audit records
- alter checkpoint configuration

## Planner Integration

The collector emits a `WalCheckpointObservation` compatible with the existing planner from:

```text
kernel/stores/sqlite/wal_checkpoint_policy.py
```

The planner remains the authority for `wal_checkpoint_plan` generation.

## Required Local Verification Commands

```bash
python3 -m unittest tests.tracer_bullet.test_wal_checkpoint_observation_collector -v
python3 -m unittest tests.tracer_bullet.test_wal_checkpoint_policy -v
python3 -m unittest tests.tracer_bullet.test_wal_checkpoint_policy_audit -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. WAL checkpoint observation collector tests pass.
2. WAL checkpoint policy planner tests pass.
3. WAL checkpoint policy audit tests pass.
4. Full tracer-bullet tests pass.
5. `make ci` passes.
6. No checkpoint execution is introduced.
7. No WAL truncation is introduced.
8. No SQLite write transaction or mutation is introduced by the collector.
9. Worktree is clean.

## Next Step

After this branch merges, the next branch should be:

```text
wal-checkpoint-plan-audit-integration-v1
```

That branch should combine observation collection and policy planning into a single non-mutating report.
