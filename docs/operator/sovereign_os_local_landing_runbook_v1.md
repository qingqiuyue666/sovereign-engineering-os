# Sovereign OS Local Landing Runbook v1

## 1. Bootstrap Local OS Runtime

From the repository root:

```bash
python3 - <<'PY'
from pathlib import Path
from kernel.os_engine.local_os_runtime import LocalOSRuntime

with LocalOSRuntime(root=Path(".local/os_engine"), repo_root=Path.cwd()) as runtime:
    print(runtime.summary().to_json())
PY
```

The runtime initializes SQLite WAL state, the event log, SQLite job queue, artifact store, human review gate, materialization planner, and built-in workers. Initialization does not execute jobs, open the GUI, launch DCC tools, or call the network.

## 2. Run SQLite ResourceWarning Check

```bash
PYTHONWARNINGS=error::ResourceWarning python3 -m unittest tests.tracer_bullet.test_os_engine_sqlite_resource_cleanup -v
PYTHONWARNINGS=error::ResourceWarning python3 -m unittest discover -s tests/tracer_bullet -v
```

Every SQLite access path must close through `OSDatabase.connect()` or an owning runtime close hook.

## 3. Run Desktop Headless Smoke

```bash
python3 -m apps.desktop_local_smoke
```

This imports the desktop module passively, reports PySide6 availability, bootstraps the OS runtime, and submits a non-GUI context-pack job through the queue and local runner. It must not open a window.

## 4. Run Context-Pack Worker

```bash
python3 - <<'PY'
from pathlib import Path
from kernel.os_engine.local_job_runner import LocalJobRunner
from kernel.os_engine.local_os_runtime import LocalOSRuntime

with LocalOSRuntime(root=Path(".local/os_engine"), repo_root=Path.cwd()) as runtime:
    job_id = "operator_context_pack"
    runtime.job_queue.create_job(
        job_id=job_id,
        job_type="context_pack",
        input_manifest={"inputs": {"changed_files_only": False, "max_files": 32}},
        output_dir=str(runtime.artifact_store.artifact_root / "context_packs"),
        local_only=True,
    )
    runtime.job_queue.admit_job(job_id)
    runtime.job_queue.enqueue_job(job_id)
    print(LocalJobRunner(runtime).run_next(job_id=job_id).to_dict())
PY
```

## 5. Run HFX_008 Dry-Run Landing Chain

```bash
python3 - <<'PY'
from pathlib import Path
from kernel.os_engine.hfx_008_landing_chain import execute_hfx_008_dry_run_chain
from kernel.os_engine.local_os_runtime import LocalOSRuntime

with LocalOSRuntime(root=Path(".local/os_engine"), repo_root=Path.cwd()) as runtime:
    print(execute_hfx_008_dry_run_chain(runtime).to_json())
PY
```

The chain records topology/proof/review/summary dry-run materializations and keeps `final_claim_allowed=false`.

## 6. Inspect SQLite Job And Artifact State

```bash
python3 - <<'PY'
from pathlib import Path
from kernel.os_engine.local_os_runtime import LocalOSRuntime

with LocalOSRuntime(root=Path(".local/os_engine"), repo_root=Path.cwd()) as runtime:
    for job in runtime.job_queue.list_jobs():
        print(job.to_json())
    for artifact in runtime.artifact_store.list_artifacts():
        print(artifact.to_json())
PY
```

## 7. Close Resources

Use `with LocalOSRuntime(...) as runtime:` for normal operation. For manual ownership, call:

```python
runtime.close()
```

Do this before removing runtime directories or handing the DB to another process.

## 8. Quarantine Failure

The local job runner writes a failure bundle artifact and moves failed unsafe execution to `quarantined` when worker execution raises:

```bash
python3 - <<'PY'
from pathlib import Path
from kernel.os_engine.local_os_runtime import LocalOSRuntime

with LocalOSRuntime(root=Path(".local/os_engine"), repo_root=Path.cwd()) as runtime:
    for artifact in runtime.artifact_store.list_artifacts():
        if artifact.artifact_type == "failure_bundle":
            print(artifact.to_json())
PY
```

Do not release a quarantined artifact without a new human review decision.

## 9. Proceed Later To Real HFX_008 Proof

After local resources and Houdini operator preflight exist, run the real proof manually outside CI:

```bash
python3 -m kernel.vfx.hfx_topology_auditor --repo-root . --asset HFX_008 --write-audit
hython kernel/vfx/hfx_single_frame_prover.py --asset HFX_008 --operator-run
python3 tools/generate_sovereign_os_landing_readiness_report.py
```

The real proof must produce a valid visual frame artifact, checksum metadata, artifact-store record, and human review approval before any final claim.

## 10. Claim Boundary

Do not claim final HFX_008 completion, production autonomy, or final physical proof until a real visual proof artifact exists, validation passes, and a human approves it through the durable gate. Dry-run artifacts are operational evidence only.
