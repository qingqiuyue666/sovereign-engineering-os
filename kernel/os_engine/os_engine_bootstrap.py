"""Deterministic bootstrap for the local-first OS engine v3 core."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.database import OSDatabase, stable_content_hash
from kernel.os_engine.sqlite_artifact_store import SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue
from kernel.os_engine.worker_registry import build_default_worker_registry


class OSEngineBootstrapError(RuntimeError):
    """Raised when the OS engine cannot be bootstrapped safely."""


@dataclass(frozen=True, slots=True)
class OSEngineStateSummary:
    root: str
    db_path: str
    schema_hash: str
    journal_mode: str
    foreign_keys: bool
    tables: tuple[str, ...]
    worker_types: tuple[str, ...]
    queue_backend: str
    artifact_store_backend: str
    executed_jobs: int
    gui_launched: bool
    external_programs_launched: int
    network_calls: int
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def bootstrap_os_engine(*, root: Path, db_name: str = "os_engine.sqlite3") -> OSEngineStateSummary:
    if not db_name or "/" in db_name or "\\" in db_name:
        raise OSEngineBootstrapError("db_name must be a local filename")
    database = OSDatabase(root=root, db_path=root / db_name)
    database_summary = database.initialize()
    SQLiteJobQueue(database)
    SQLiteArtifactStore(database=database, artifact_root=Path(database_summary.root) / "artifacts").initialize()
    registry = build_default_worker_registry()
    payload = {
        "artifact_store_backend": "sqlite",
        "db_path": database_summary.db_path,
        "executed_jobs": 0,
        "external_programs_launched": 0,
        "foreign_keys": database_summary.foreign_keys,
        "gui_launched": False,
        "journal_mode": database_summary.journal_mode,
        "network_calls": 0,
        "queue_backend": "sqlite_event_sourced",
        "root": database_summary.root,
        "schema_hash": database_summary.schema_hash,
        "tables": database_summary.tables,
        "worker_types": tuple(registry.registered_types()),
    }
    return OSEngineStateSummary(content_hash=stable_content_hash(payload), **payload)
