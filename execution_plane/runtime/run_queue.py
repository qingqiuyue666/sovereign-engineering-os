"""Run queue for controlled execution jobs."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import utc_now
from execution_plane.runtime.state_ledger import state_event

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELED"}


@dataclass(frozen=True)
class RunJob:
    job_id: str
    adapter: str
    action: str
    permit: Mapping[str, Any]
    payload: Mapping[str, Any]
    status: str = "QUEUED"


class InMemoryRunQueue:
    def __init__(self) -> None:
        self._pending: deque[RunJob] = deque()
        self._jobs: dict[str, RunJob] = {}

    def enqueue(self, permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> RunJob:
        adapter = str(permit.get("allowed_adapter", ""))
        action = str(permit.get("allowed_action", ""))
        job_id = stable_id("JOB", permit.get("permit_id", ""), adapter, action, utc_now())
        job = RunJob(job_id=job_id, adapter=adapter, action=action, permit=dict(permit), payload=dict(payload or {}))
        self._pending.append(job)
        self._jobs[job_id] = job
        return job

    def pop_next(self) -> RunJob | None:
        if not self._pending:
            return None
        job = self._pending.popleft()
        running = _replace_status(job, "RUNNING")
        self._jobs[job.job_id] = running
        return running

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return False
        self._jobs[job_id] = _replace_status(job, "CANCELED")
        self._pending = deque(item for item in self._pending if item.job_id != job_id)
        return True

    def mark(self, job_id: str, status: str) -> None:
        job = self._jobs[job_id]
        self._jobs[job_id] = _replace_status(job, status)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "job_id": job.job_id,
                "adapter": job.adapter,
                "action": job.action,
                "status": job.status,
            }
            for job in self._jobs.values()
        ]

    def inspect(self, job_id: str) -> dict[str, Any]:
        job = self._jobs[job_id]
        return {
            "job_id": job.job_id,
            "adapter": job.adapter,
            "action": job.action,
            "status": job.status,
            "permit_id": job.permit.get("permit_id"),
        }


def _replace_status(job: RunJob, status: str) -> RunJob:
    return RunJob(
        job_id=job.job_id,
        adapter=job.adapter,
        action=job.action,
        permit=job.permit,
        payload=job.payload,
        status=status,
    )


class FileRunQueue:
    """Small durable queue rooted in the local workspace."""

    def __init__(self, root: str | Path = "work/run_queue") -> None:
        self.root = Path(root)
        self.state_path = self.root / "run_queue_state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def enqueue_rpc_template(self, template_path: str | Path) -> dict[str, Any]:
        path = Path(template_path)
        payload = load_json(path)
        run_id = stable_id("RUNQ", path.as_posix(), utc_now())
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / "rpc_template.json", payload)
        record = {
            "run_id": run_id,
            "kind": "rpc_template",
            "template_path": path.as_posix(),
            "status": "QUEUED",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "state_transitions": [],
            "result": None,
            "error": None,
        }
        record = self._transition(record, "QUEUED")
        state = self._read_state()
        state["runs"].append(record)
        self._write_state(state)
        return dict(record)

    def list_runs(self) -> list[dict[str, Any]]:
        return [
            {
                "run_id": run["run_id"],
                "status": run["status"],
                "kind": run.get("kind"),
                "template_path": run.get("template_path"),
                "updated_at": run.get("updated_at"),
            }
            for run in self._read_state()["runs"]
        ]

    def inspect(self, run_id: str) -> dict[str, Any]:
        return dict(self._find_run(run_id))

    def cancel(self, run_id: str) -> dict[str, Any]:
        state = self._read_state()
        for index, run in enumerate(state["runs"]):
            if run["run_id"] != run_id:
                continue
            if run["status"] in TERMINAL_STATUSES:
                return dict(run)
            state["runs"][index] = self._transition(run, "CANCELED", {"cancel_requested": True})
            self._write_state(state)
            return dict(state["runs"][index])
        raise KeyError(run_id)

    def process_next(self, dispatch: Any | None = None) -> dict[str, Any] | None:
        from execution_plane.rpc_gateway import invoke_rpc_file

        dispatcher = dispatch or invoke_rpc_file
        claimed = self._claim_next()
        if claimed is None:
            return None
        run_id = str(claimed["run_id"])
        template_path = self.root / run_id / "rpc_template.json"
        try:
            result = dispatcher(template_path)
        except TimeoutError as exc:
            return self._finish(run_id, "TIMED_OUT", result=None, error=f"TIMEOUT: {exc}")
        except Exception as exc:
            return self._finish(run_id, "FAILED", result=None, error=f"{exc.__class__.__name__}: {exc}")
        terminal = "SUCCEEDED"
        response_result = result.get("result") if isinstance(result, Mapping) else None
        if isinstance(response_result, Mapping) and response_result.get("terminal_status") != "TERMINAL_SUCCEEDED":
            terminal = "FAILED"
        if isinstance(result, Mapping) and "error" in result:
            terminal = "FAILED"
        return self._finish(run_id, terminal, result=result, error=None)

    def _claim_next(self) -> dict[str, Any] | None:
        state = self._read_state()
        for index, run in enumerate(state["runs"]):
            if run["status"] == "QUEUED":
                state["runs"][index] = self._transition(run, "RUNNING")
                self._write_state(state)
                return dict(state["runs"][index])
        return None

    def _finish(
        self,
        run_id: str,
        status: str,
        *,
        result: Mapping[str, Any] | None,
        error: str | None,
    ) -> dict[str, Any]:
        state = self._read_state()
        for index, run in enumerate(state["runs"]):
            if run["run_id"] != run_id:
                continue
            updated = dict(run)
            updated["result"] = dict(result or {}) if result is not None else None
            updated["error"] = error
            updated = self._transition(updated, status, {"error": error} if error else {})
            state["runs"][index] = updated
            self._write_state(state)
            run_dir = self.root / run_id
            if result is not None:
                write_json(run_dir / "result.json", result)
            if error is not None:
                write_json(run_dir / "failure_bundle.json", {"schema_version": "seos.run_queue.failure.v1", "run_id": run_id, "error": error})
            return dict(updated)
        raise KeyError(run_id)

    def _transition(self, run: Mapping[str, Any], status: str, detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
        updated = dict(run)
        updated["status"] = status
        updated["updated_at"] = utc_now()
        event = state_event(
            run_id=str(updated["run_id"]),
            adapter="run_queue",
            state=status,
            detail=dict(detail or {}),
        )
        transitions = [dict(item) for item in updated.get("state_transitions", []) if isinstance(item, Mapping)]
        transitions.append(event)
        updated["state_transitions"] = transitions
        self._append_ledger(str(updated["run_id"]), event)
        return updated

    def _append_ledger(self, run_id: str, event: Mapping[str, Any]) -> None:
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = run_dir / "state_ledger.jsonl"
        with ledger_path.open("a", encoding="utf-8") as handle:
            import json

            handle.write(json.dumps(dict(event), sort_keys=True) + "\n")

    def _find_run(self, run_id: str) -> Mapping[str, Any]:
        for run in self._read_state()["runs"]:
            if run["run_id"] == run_id:
                return run
        raise KeyError(run_id)

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": "seos.run_queue.v1", "runs": []}
        state = load_json(self.state_path)
        if not isinstance(state.get("runs"), list):
            state["runs"] = []
        return state

    def _write_state(self, state: Mapping[str, Any]) -> None:
        write_json(self.state_path, state)
