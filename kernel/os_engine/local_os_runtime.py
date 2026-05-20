"""Local landed OS runtime facade for SQLite-backed execution paths."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.builtin_workers import build_builtin_worker_registry
from kernel.os_engine.database import OSDatabase, stable_content_hash
from kernel.os_engine.event_log import EventLog
from kernel.os_engine.human_review_gate import HumanReviewGate
from kernel.os_engine.materialization import decide_materialization
from kernel.os_engine.schema_version import SCHEMA_VERSION
from kernel.os_engine.sqlite_artifact_store import SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue
from kernel.os_engine.worker_registry import WorkerRegistry


class LocalOSRuntimeError(RuntimeError):
    """Raised when the local runtime cannot bootstrap safely."""


@dataclass(frozen=True, slots=True)
class LocalOSRuntimeSummary:
    root: str
    repo_root: str
    db_path: str
    artifact_root: str
    schema_version: int
    schema_hash: str
    journal_mode: str
    registered_workers: tuple[str, ...]
    job_count: int
    artifact_count: int
    human_review_count: int
    materialization_count: int
    executed_jobs_on_init: int
    gui_launched: bool
    external_programs_launched_on_init: int
    network_calls_on_init: int
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class MaterializationPlanner:
    decide = staticmethod(decide_materialization)


class LocalOSRuntime:
    """Small resource-owning facade over the v3 OS engine components."""

    def __init__(self, *, root: Path, repo_root: Path | None = None, db_name: str = "os_engine.sqlite3") -> None:
        if not db_name or "/" in db_name or "\\" in db_name:
            raise LocalOSRuntimeError("db_name must be a filename inside the runtime root")
        self.root = root.expanduser().resolve(strict=False)
        self.repo_root = (repo_root or Path.cwd()).expanduser().resolve(strict=False)
        self.database = OSDatabase(root=self.root, db_path=self.root / db_name)
        self.database_summary = self.database.initialize()
        self.event_log = EventLog(self.database)
        self.job_queue = SQLiteJobQueue(self.database)
        self.artifact_store = SQLiteArtifactStore(database=self.database, artifact_root=self.root / "artifacts")
        self.artifact_store.initialize()
        self.human_review_gate = HumanReviewGate(self.database)
        self.materialization_planner = MaterializationPlanner()
        self.worker_registry: WorkerRegistry = build_builtin_worker_registry()
        self._closed = False

    def __enter__(self) -> "LocalOSRuntime":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        _ = (exc_type, exc, traceback)
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self.job_queue.close()
        self.artifact_store.close()
        self.human_review_gate.close()
        self.event_log.close()
        self.database.close()
        self._closed = True

    def resolve_runtime_path(self, relative_path: str | Path) -> Path:
        self._ensure_open()
        raw = Path(relative_path)
        path = raw if raw.is_absolute() else self.root / raw
        resolved = path.expanduser().resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise LocalOSRuntimeError(f"runtime path escapes root: {resolved}")
        return resolved

    def summary(self) -> LocalOSRuntimeSummary:
        self._ensure_open()
        with self.database.connect() as connection:
            job_count = int(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
            artifact_count = int(connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
            review_count = int(connection.execute("SELECT COUNT(*) FROM human_reviews").fetchone()[0])
            materialization_count = int(connection.execute("SELECT COUNT(*) FROM materializations").fetchone()[0])
        payload = {
            "artifact_count": artifact_count,
            "artifact_root": str(self.artifact_store.artifact_root),
            "db_path": str(self.database.db_path),
            "executed_jobs_on_init": 0,
            "external_programs_launched_on_init": 0,
            "gui_launched": False,
            "human_review_count": review_count,
            "job_count": job_count,
            "journal_mode": self.database_summary.journal_mode,
            "materialization_count": materialization_count,
            "network_calls_on_init": 0,
            "registered_workers": tuple(self.worker_registry.registered_types()),
            "repo_root": str(self.repo_root),
            "root": str(self.root),
            "schema_hash": self.database_summary.schema_hash,
            "schema_version": SCHEMA_VERSION,
        }
        return LocalOSRuntimeSummary(content_hash=stable_content_hash(payload), **payload)

    def _ensure_open(self) -> None:
        if self._closed:
            raise LocalOSRuntimeError("local OS runtime is closed")
