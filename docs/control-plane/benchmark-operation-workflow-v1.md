# Benchmark Operation Workflow V1

Status: `implemented_local_external_benchmark_pending`

This workflow separates repo-local benchmark readiness from external benchmark
evidence.

## Repo-Local Benchmark Cycle

1. Select a user-style task fixture from `reports/control-plane/task-fixtures-v1.json`.
2. Classify risk and policy decision.
3. Run only local safe validation.
4. Record result in `reports/control-plane/first-controlled-cycle-v1.json`.
5. Update recurring benchmark queue.

## External Benchmark Candidates

Candidate families include SWE-bench Verified, SWE-rebench, OpenHands runtime
evaluations, repository-local acceptance tests, and buyer-defined workflow
samples. Candidate use requires license, contamination, environment, and
authorization review.

## Environment Requirements

External benchmark execution requires a clean workspace, pinned commit,
documented dependencies, allowed network boundary, artifact capture, command
transcript, result parser, contamination review, and reviewer signoff.

## Blocker And Resume

External benchmark execution is blocked until a human authorizes the benchmark,
environment, cost, and result-use policy. Resume from
`reports/control-plane/resume-point-v1.json` after authorization.

## Result Interpretation

Passing local fixtures does not support external benchmark claims. External
results may support only the exact task, environment, date, and version tested.

## Claim Policy

Do not claim externally benchmark-proven unless the external evidence ledger
contains source, actor, date, artifact, claim supported, claim not supported,
confidence, and next action for the benchmark run.

