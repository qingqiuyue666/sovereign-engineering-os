# Patch Repair Jobs Runbook

## Create A Job

```bash
python3 seos.py repair create examples/repair/schema_invalid_failure_bundle.json --json
```

This reads the physical failure bundle, classifies it as a code/schema repair candidate, writes a `PatchRepairJob`, copies the source bundle, and appends a repair ledger event under:

```text
work/repair_jobs/
```

## Invoke Local Tool Bridge

Use the `job_path` returned by `repair create`:

```bash
python3 seos.py repair invoke work/repair_jobs/<repair_id>/patch_repair_job.json --json
```

The bridge only executes a non-interactive `tool_command` that is explicitly configured on a job or injected by a caller. Without that configured command, this writes `repair_failure_bundle.json` with `LOCAL_TOOL_UNAVAILABLE`. That is the expected truthful unavailable path.

## Apply Handler

```bash
python3 seos.py repair apply work/repair_jobs/<repair_id>/patch_repair_job.json candidate.patch --json
```

By default `auto_apply` is false, so the handler writes `patch_apply_blocked.json` and refuses to mutate the repo until an operator-reviewed policy enables application.

## CI-Safe Path

`tests/tracer_bullet/test_patch_repair_jobs_v1.py` exercises classification, job writing, local tool invocation with an injected command, unavailable tool failure bundles, policy-blocked patch apply, and repair ledger replay.
