"""SQLite WAL checkpoint policy audit.

This module audits whether the repository declares a WAL checkpoint policy. It
never opens a live database connection, never runs PRAGMA wal_checkpoint, never
truncates WAL files, and never mutates SQLite state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = ["WalCheckpointPolicyAuditResult", "run_wal_checkpoint_policy_audit"]

_REPORT_FILE = "wal_checkpoint_policy_audit_report.json"
_REPORT_TYPE = "seos_wal_checkpoint_policy_audit_v1"

_REQUIRED_OPENER_MARKERS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA busy_timeout=5000;",
)

_CHECKPOINT_POLICY_MARKERS = (
    "wal_autocheckpoint",
    "wal_checkpoint",
    "checkpoint_policy",
    "WALCheckpointPolicy",
    "max_wal_pages",
    "max_wal_bytes",
    "trigger_on_snapshot",
    "checkpoint_before_snapshot",
)

_MUTATING_CHECKPOINT_MARKERS = (
    "PRAGMA wal_checkpoint",
    "wal_checkpoint(",
    "sqlite3_wal_checkpoint",
    "SQLITE_CHECKPOINT_TRUNCATE",
    "TRUNCATE",
)


@dataclass(frozen=True)
class WalCheckpointPolicyAuditResult:
    output_dir: Path
    report_path: Path
    complete: bool
    wal_mode_declared: bool
    explicit_checkpoint_policy_found: bool
    mutating_checkpoint_executed: bool
    required_human_approval: bool


def run_wal_checkpoint_policy_audit(
    *,
    repo_root: Path,
    output_dir: Path,
) -> WalCheckpointPolicyAuditResult:
    root = Path(repo_root)
    out = Path(output_dir)
    if not root.exists() or not root.is_dir():
        raise ValueError("repo_root is missing")
    if not out.exists() or not out.is_dir():
        raise ValueError("output_dir is missing")
    report_path = out / _REPORT_FILE
    if report_path.exists():
        raise ValueError("wal checkpoint policy audit report already exists")

    opener_path = root / "kernel" / "stores" / "sqlite" / "wal_recovery.py"
    migration_path = (
        root
        / "kernel"
        / "stores"
        / "sqlite"
        / "migrations"
        / "0001_core_signable_path.sql"
    )
    snapshot_schema_path = root / "kernel" / "schemas" / "snapshot_root.schema.json"

    opener_text = _read_text(opener_path)
    migration_text = _read_text(migration_path)
    snapshot_schema_text = _read_text(snapshot_schema_path)

    opener_markers = {marker: marker in opener_text for marker in _REQUIRED_OPENER_MARKERS}
    wal_mode_declared = opener_markers["PRAGMA journal_mode=WAL;"]
    synchronous_normal_declared = opener_markers["PRAGMA synchronous=NORMAL;"]
    checkpoint_policy_hits = _collect_policy_hits(root)
    explicit_checkpoint_policy_found = bool(checkpoint_policy_hits)

    report = {
        "report_type": _REPORT_TYPE,
        "complete": True,
        "repo_root": root.as_posix(),
        "wal_mode_declared": wal_mode_declared,
        "synchronous_normal_declared": synchronous_normal_declared,
        "opener_path": opener_path.as_posix(),
        "opener_required_markers": opener_markers,
        "migration_mentions_wal_posture": "journal_mode = WAL" in migration_text,
        "snapshot_schema_has_root_hash": "root_hash" in snapshot_schema_text,
        "snapshot_schema_has_file_manifest_hash": "file_manifest_hash" in snapshot_schema_text,
        "snapshot_schema_has_artifact_manifest_hash": "artifact_manifest_hash" in snapshot_schema_text,
        "explicit_checkpoint_policy_found": explicit_checkpoint_policy_found,
        "checkpoint_policy_hits": checkpoint_policy_hits,
        "checkpoint_runner_found": any(
            "wal_checkpoint" in hit["matched_text"] or "WALCheckpointPolicy" in hit["matched_text"]
            for hit in checkpoint_policy_hits
        ),
        "snapshot_trigger_rule_found": any(
            "trigger_on_snapshot" in hit["matched_text"]
            or "checkpoint_before_snapshot" in hit["matched_text"]
            for hit in checkpoint_policy_hits
        ),
        "wal_size_threshold_rule_found": any(
            "max_wal_pages" in hit["matched_text"]
            or "max_wal_bytes" in hit["matched_text"]
            or "wal_autocheckpoint" in hit["matched_text"]
            for hit in checkpoint_policy_hits
        ),
        "audit_only": True,
        "mutating_checkpoint_executed": False,
        "database_opened": False,
        "pragma_wal_checkpoint_executed": False,
        "wal_truncate_executed": False,
        "sqlite_state_mutated": False,
        "recommended_next_step": "wal_checkpoint_policy_foundation_v1",
        "required_human_approval": True,
    }
    write_json_atomically(report_path, report)
    return WalCheckpointPolicyAuditResult(
        output_dir=out,
        report_path=report_path,
        complete=True,
        wal_mode_declared=wal_mode_declared,
        explicit_checkpoint_policy_found=explicit_checkpoint_policy_found,
        mutating_checkpoint_executed=False,
        required_human_approval=True,
    )


def _collect_policy_hits(repo_root: Path) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    search_roots = (
        repo_root / "kernel" / "stores" / "sqlite",
        repo_root / "kernel" / "lifecycle",
        repo_root / "docs",
        repo_root / "governance",
        repo_root / "tests",
        repo_root / "validation" / "tests",
    )
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in sorted(search_root.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".md", ".txt", ".sql", ".json"):
                continue
            rel = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8")
            for marker in _CHECKPOINT_POLICY_MARKERS:
                if marker in text:
                    hits.append({"path": rel, "matched_text": marker})
    return hits


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise ValueError(path.as_posix() + " is missing")
    return path.read_text(encoding="utf-8")
