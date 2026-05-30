# Reliability Baseline V1

External review required: yes.

This baseline records a repository-local reliability check for Wave 8. It is a
repeatable engineering gate for the current evidence set, not a production
availability statement and not a final-signoff claim.

## Scope

- repeated smoke loop, target 50
- multi-task batch, target 20
- multi-workspace checks, target 3
- approval/reject/run mixed flow, target 20
- evidence/replay batch validation, target 20
- failure-path batch validation, target 10
- elapsed time recording
- flake rate recording

## Baseline Results

The committed report is `reports/reliability/reliability_benchmark_v1.json`.
The script `scripts/reliability_benchmark_v1.py` runs the checks and validates
the report without rewriting tracked files.

| Check | Target | Committed result |
| --- | ---: | ---: |
| repeated smoke loop | 50 | 50 passed |
| multi-task batch | 20 | 20 passed |
| multi-workspace checks | 3 | 3 passed |
| approval/reject/run mixed flow | 20 | 20 passed |
| evidence/replay batch validation | 20 | 20 passed |
| failure-path batch validation | 10 | 10 passed |

## Recording Rules

Elapsed time recording is emitted by the benchmark script on every run as
`elapsed_seconds`. The report stores the committed baseline field and the
maximum expected runtime ceiling so CI can fail if the benchmark becomes slow
or non-deterministic.

Flake rate recording is computed as `observed_flake_count / sample_count`.
The Wave 8 baseline sample count is 123 and the committed observed flake rate
is 0.0.

## Boundaries

The benchmark does not access network resources, does not read secret values,
and does not enable live providers. Multi-workspace checks use temporary local
workspaces that are removed after the run. External review and longer
operation-period evidence remain separate from this baseline.
