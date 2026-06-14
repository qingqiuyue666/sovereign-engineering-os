# Codex Real Task Throughput Layer

Layer id: `REAL_TASK_THROUGHPUT_LAYER`

## Purpose

Record real repository tasks as consecutive work units with start state, action,
diff summary, checks, result, and remaining risk.

## Connected Loop

real task ledger -> runtime state ledger

The active ledger is
`reports/checkpoints/real-task-throughput-ledger-v1.md`. It feeds
`reports/checkpoints/runtime-state-ledger-v1.md` and the final report.

## Evidence Gate

- `REAL_DELIVERY_BENCHMARK_RUN_01` must include changed files, validation
  evidence, and result.
- A second safe micro-task must be recorded when safe; if not safe, the exact
  blocker and next smallest action must be recorded.
- Throughput evidence is early sample evidence only, not long-term autonomy.

## Non-Claim Boundary

One or two tasks do not prove continuous autonomous maturity or production
operation.
