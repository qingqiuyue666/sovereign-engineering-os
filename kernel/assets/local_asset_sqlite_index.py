"""Per-scan SQLite query index for generated local asset scan artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
import json
import sqlite3

from kernel.assets.local_asset_schema import (
    ASSET_INDEX_FILE,
    ASSET_MANIFEST_FILE,
    AUDIT_LOG_FILE,
    DUPLICATES_REPORT_FILE,
    MEDIA_INVENTORY_FILE,
    QUARANTINE_MANIFEST_FILE,
    VALIDATION_REPORT_FILE,
)
from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file

__all__ = [
    "LOCAL_ASSET_SQLITE_INDEX_FILE",
    "LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE",
    "LOCAL_ASSET_SQLITE_OUTPUT_FILENAMES",
    "LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE",
    "LOCAL_ASSET_SQLITE_SCHEMA_TABLES",
    "LOCAL_ASSET_SQLITE_SCHEMA_VERSION",
    "LocalAssetSQLiteIndexResult",
    "build_local_asset_sqlite_index",
    "validate_local_asset_sqlite_index",
]

LOCAL_ASSET_SQLITE_INDEX_FILE = "local_asset_index.sqlite"
LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE = "local_asset_sqlite_index_manifest.json"
LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE = "local_asset_sqlite_query_summary.md"
LOCAL_ASSET_SQLITE_OUTPUT_FILENAMES = (
    LOCAL_ASSET_SQLITE_INDEX_FILE,
    LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
    LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE,
)

LOCAL_ASSET_SQLITE_SCHEMA_VERSION = "local_asset_sqlite_index_schema_v1"
LOCAL_ASSET_SQLITE_SCHEMA_TABLES = (
    "scan_runs",
    "assets",
    "duplicate_groups",
    "quarantine_events",
    "artifact_sources",
    "index_metadata",
)

_MANIFEST_TYPE = "local_asset_sqlite_index_manifest_v1"
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_query_index_only"
_NEXT_ALLOWED_ACTION = "human_query_local_asset_sqlite_index"

_SOURCE_ARTIFACTS = (
    ("asset_manifest", ASSET_MANIFEST_FILE),
    ("asset_index", ASSET_INDEX_FILE),
    ("duplicates_report", DUPLICATES_REPORT_FILE),
    ("media_inventory", MEDIA_INVENTORY_FILE),
    ("asset_runtime_audit_log", AUDIT_LOG_FILE),
    ("asset_runtime_validation_report", VALIDATION_REPORT_FILE),
    ("asset_runtime_quarantine_manifest", QUARANTINE_MANIFEST_FILE),
)

_CREATE_TABLE_SQL = (
    """
    CREATE TABLE scan_runs (
      scan_run_id TEXT PRIMARY KEY,
      project_id TEXT,
      input_dir TEXT,
      output_dir TEXT,
      recursive INTEGER,
      include_hidden INTEGER,
      files_scanned INTEGER,
      bytes_scanned INTEGER,
      duplicate_groups INTEGER,
      quarantined_paths INTEGER,
      asset_manifest_sha256 TEXT,
      asset_index_sha256 TEXT,
      duplicates_report_sha256 TEXT,
      quarantine_manifest_sha256 TEXT,
      validation_report_sha256 TEXT,
      audit_log_sha256 TEXT
    )
    """,
    """
    CREATE TABLE assets (
      asset_id TEXT PRIMARY KEY,
      scan_run_id TEXT,
      relative_path TEXT,
      path TEXT,
      file_name TEXT,
      extension TEXT,
      media_class TEXT,
      size_bytes INTEGER,
      sha256 TEXT,
      is_duplicate INTEGER,
      duplicate_group_id TEXT,
      is_quarantined INTEGER,
      quarantine_reason TEXT,
      content_indexed INTEGER DEFAULT 0,
      raw_content_copied INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE duplicate_groups (
      duplicate_group_id TEXT PRIMARY KEY,
      scan_run_id TEXT,
      sha256 TEXT,
      asset_count INTEGER,
      total_size_bytes INTEGER
    )
    """,
    """
    CREATE TABLE quarantine_events (
      quarantine_event_id TEXT PRIMARY KEY,
      scan_run_id TEXT,
      relative_path TEXT,
      path TEXT,
      reason TEXT,
      severity TEXT,
      raw_content_copied INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE artifact_sources (
      artifact_role TEXT PRIMARY KEY,
      path TEXT,
      sha256 TEXT,
      size_bytes INTEGER
    )
    """,
    """
    CREATE TABLE index_metadata (
      key TEXT PRIMARY KEY,
      value TEXT
    )
    """,
)

_CREATE_INDEX_SQL = (
    "CREATE INDEX assets_extension_idx ON assets(extension, relative_path)",
    "CREATE INDEX assets_media_class_idx ON assets(media_class, relative_path)",
    "CREATE INDEX assets_size_idx ON assets(size_bytes DESC, relative_path)",
    "CREATE INDEX duplicate_groups_sha256_idx ON duplicate_groups(sha256)",
    "CREATE INDEX quarantine_events_reason_idx ON quarantine_events(reason, relative_path)",
)


@dataclass(frozen=True)
class LocalAssetSQLiteIndexResult:
    output_dir: Path
    database_path: Path
    manifest_path: Path
    query_summary_path: Path
    scan_run_id: str
    row_counts: dict[str, int]
    source_artifacts: list[dict[str, object]]
    database_sha256: str
    database_size_bytes: int
    schema_version: str = LOCAL_ASSET_SQLITE_SCHEMA_VERSION


def build_local_asset_sqlite_index(
    output_dir: Path,
    *,
    input_dir: Path,
    project_id: str | None = None,
    recursive: bool | None = None,
    include_hidden: bool | None = None,
) -> LocalAssetSQLiteIndexResult:
    """Build a deterministic metadata-only SQLite index inside one scan output dir."""

    output_path = _validate_output_dir(output_dir)
    input_path = Path(input_dir)
    database_path, manifest_path, query_summary_path = _sqlite_output_paths(output_path)
    _require_outputs_absent(database_path, manifest_path, query_summary_path)

    source_artifacts = _source_artifact_records(output_path)
    source_hashes = {
        str(artifact["artifact_role"]): str(artifact["sha256"])
        for artifact in source_artifacts
    }
    asset_manifest = _read_json_source(output_path / ASSET_MANIFEST_FILE, "asset_manifest")
    _read_json_source(output_path / ASSET_INDEX_FILE, "asset_index")
    duplicates_report = _read_json_source(
        output_path / DUPLICATES_REPORT_FILE,
        "duplicates_report",
    )
    validation_report = _read_json_source(
        output_path / VALIDATION_REPORT_FILE,
        "asset_runtime_validation_report",
    )
    quarantine_manifest = _read_json_source(
        output_path / QUARANTINE_MANIFEST_FILE,
        "asset_runtime_quarantine_manifest",
    )

    scan = _scan_run_record(
        asset_manifest=asset_manifest,
        validation_report=validation_report,
        duplicates_report=duplicates_report,
        quarantine_manifest=quarantine_manifest,
        source_hashes=source_hashes,
        input_dir=input_path,
        output_dir=output_path,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    assets = _asset_rows(
        asset_manifest=asset_manifest,
        duplicates_report=duplicates_report,
        input_dir=input_path,
        scan_run_id=scan["scan_run_id"],
    )
    duplicate_groups = _duplicate_group_rows(
        assets=assets,
        duplicates_report=duplicates_report,
        scan_run_id=scan["scan_run_id"],
    )
    quarantine_events = _quarantine_event_rows(
        quarantine_manifest=quarantine_manifest,
        input_dir=input_path,
        scan_run_id=scan["scan_run_id"],
    )
    metadata = _index_metadata(
        scan_run_id=scan["scan_run_id"],
        source_artifacts=source_artifacts,
    )

    row_counts = {
        "scan_runs": 1,
        "assets": len(assets),
        "duplicate_groups": len(duplicate_groups),
        "quarantine_events": len(quarantine_events),
        "artifact_sources": len(source_artifacts),
        "index_metadata": len(metadata),
    }

    _write_sqlite_database(
        database_path=database_path,
        scan=scan,
        assets=assets,
        duplicate_groups=duplicate_groups,
        quarantine_events=quarantine_events,
        source_artifacts=source_artifacts,
        metadata=metadata,
    )

    database_sha256 = sha256_file(database_path)
    database_size_bytes = database_path.stat().st_size
    manifest_payload = _manifest_payload(
        database_path=database_path,
        manifest_path=manifest_path,
        query_summary_path=query_summary_path,
        scan_run_id=scan["scan_run_id"],
        row_counts=row_counts,
        source_artifacts=source_artifacts,
        database_sha256=database_sha256,
        database_size_bytes=database_size_bytes,
    )
    _write_json_exclusive(manifest_path, manifest_payload)
    _write_text_exclusive(
        query_summary_path,
        _query_summary_markdown(
            database_path=database_path,
            scan=scan,
            row_counts=row_counts,
            assets=assets,
            duplicate_groups=duplicate_groups,
            quarantine_events=quarantine_events,
        ),
    )

    return LocalAssetSQLiteIndexResult(
        output_dir=output_path,
        database_path=database_path,
        manifest_path=manifest_path,
        query_summary_path=query_summary_path,
        scan_run_id=str(scan["scan_run_id"]),
        row_counts=row_counts,
        source_artifacts=source_artifacts,
        database_sha256=database_sha256,
        database_size_bytes=database_size_bytes,
    )


def validate_local_asset_sqlite_index(output_dir: Path) -> dict[str, object]:
    """Validate the per-scan SQLite index and manifest without mutating it."""

    output_path = _validate_output_dir(output_dir)
    database_path, manifest_path, query_summary_path = _sqlite_output_paths(output_path)
    manifest = _read_json_source(manifest_path, "local_asset_sqlite_index_manifest")
    if manifest.get("database_sha256") != sha256_file(database_path):
        raise ValueError("local asset sqlite database hash mismatch")
    if manifest.get("database_size_bytes") != database_path.stat().st_size:
        raise ValueError("local asset sqlite database size mismatch")
    if manifest.get("query_summary_path") != query_summary_path.as_posix():
        raise ValueError("local asset sqlite query summary path mismatch")
    if not query_summary_path.is_file() or query_summary_path.is_symlink():
        raise ValueError("local asset sqlite query summary is missing")

    connection = _connect_readonly(database_path)
    try:
        tables = tuple(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        )
        missing_tables = [
            table for table in LOCAL_ASSET_SQLITE_SCHEMA_TABLES if table not in tables
        ]
        if missing_tables:
            raise ValueError("local asset sqlite expected table missing")
        row_counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in LOCAL_ASSET_SQLITE_SCHEMA_TABLES
        }
    finally:
        connection.close()

    if manifest.get("row_counts") != row_counts:
        raise ValueError("local asset sqlite row count mismatch")
    return {
        "valid": True,
        "database_path": database_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "query_summary_path": query_summary_path.as_posix(),
        "schema_tables": list(tables),
        "row_counts": row_counts,
        "scan_run_id": manifest.get("scan_run_id"),
    }


def _validate_output_dir(output_dir: Path) -> Path:
    output_path = Path(output_dir)
    if not output_path.exists():
        raise ValueError("local asset sqlite output_dir is missing")
    if not output_path.is_dir():
        raise ValueError("local asset sqlite output_dir is not a directory")
    if output_path.is_symlink():
        raise ValueError("local asset sqlite output_dir must not be a symlink")
    return output_path


def _sqlite_output_paths(output_path: Path) -> tuple[Path, Path, Path]:
    return (
        output_path / LOCAL_ASSET_SQLITE_INDEX_FILE,
        output_path / LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
        output_path / LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE,
    )


def _require_outputs_absent(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            raise ValueError("local asset sqlite index output already exists: " + path.name)


def _source_artifact_records(output_path: Path) -> list[dict[str, object]]:
    records = []
    for artifact_role, file_name in _SOURCE_ARTIFACTS:
        path = output_path / file_name
        _require_source_file(output_path, path, artifact_role)
        records.append(
            {
                "artifact_role": artifact_role,
                "path": path.as_posix(),
                "relative_path": file_name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "content_indexed": False,
                "raw_content_copied": False,
            }
        )
    return sorted(records, key=lambda record: str(record["artifact_role"]))


def _require_source_file(output_path: Path, path: Path, artifact_role: str) -> None:
    try:
        path.resolve(strict=False).relative_to(output_path.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ValueError("local asset sqlite source artifact escapes output_dir") from error
    if path.is_symlink():
        raise ValueError("local asset sqlite source artifact is a symlink: " + artifact_role)
    if not path.is_file():
        raise ValueError("local asset sqlite source artifact is missing: " + artifact_role)


def _read_json_source(path: Path, artifact_role: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "local asset sqlite source artifact is malformed: " + artifact_role
        ) from error
    if not isinstance(payload, dict):
        raise ValueError("local asset sqlite source artifact is malformed: " + artifact_role)
    return payload


def _scan_run_record(
    *,
    asset_manifest: dict,
    validation_report: dict,
    duplicates_report: dict,
    quarantine_manifest: dict,
    source_hashes: dict[str, str],
    input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool | None,
    include_hidden: bool | None,
) -> dict[str, object]:
    manifest_project_id = asset_manifest.get("project_id")
    if project_id is not None and project_id != manifest_project_id:
        raise ValueError("local asset sqlite project_id does not match asset manifest")
    input_section = _dict_field(asset_manifest, "input", "asset_manifest")
    manifest_recursive = _bool_field(input_section, "recursive", "asset_manifest.input")
    manifest_include_hidden = _bool_field(
        input_section,
        "include_hidden",
        "asset_manifest.input",
    )
    if recursive is not None and bool(recursive) != manifest_recursive:
        raise ValueError("local asset sqlite recursive flag does not match asset manifest")
    if include_hidden is not None and bool(include_hidden) != manifest_include_hidden:
        raise ValueError(
            "local asset sqlite include_hidden flag does not match asset manifest"
        )

    manifest_counts = _dict_field(asset_manifest, "counts", "asset_manifest")
    validation_counts = _dict_field(validation_report, "counts", "validation_report")
    files_scanned = _int_field(manifest_counts, "files_scanned", "asset_manifest.counts")
    bytes_scanned = _int_field(manifest_counts, "bytes_scanned", "asset_manifest.counts")
    duplicate_groups = _int_field(
        manifest_counts,
        "duplicate_sha256_groups",
        "asset_manifest.counts",
    )
    quarantined_paths = _int_field(
        manifest_counts,
        "quarantined_paths",
        "asset_manifest.counts",
    )
    if files_scanned != _int_field(validation_counts, "files_scanned", "validation_report.counts"):
        raise ValueError("local asset sqlite file count mismatch")
    if duplicate_groups != _int_field(
        duplicates_report,
        "duplicate_sha256_group_count",
        "duplicates_report",
    ):
        raise ValueError("local asset sqlite duplicate group count mismatch")
    if quarantined_paths != _int_field(
        quarantine_manifest,
        "quarantined_path_count",
        "quarantine_manifest",
    ):
        raise ValueError("local asset sqlite quarantine count mismatch")

    scan_run_id = _scan_run_id(
        asset_manifest_sha256=source_hashes["asset_manifest"],
        input_dir=input_dir.as_posix(),
        output_dir=output_dir.as_posix(),
        project_id=manifest_project_id,
        recursive=manifest_recursive,
        include_hidden=manifest_include_hidden,
    )
    return {
        "scan_run_id": scan_run_id,
        "project_id": manifest_project_id,
        "input_dir": input_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "recursive": int(manifest_recursive),
        "include_hidden": int(manifest_include_hidden),
        "files_scanned": files_scanned,
        "bytes_scanned": bytes_scanned,
        "duplicate_groups": duplicate_groups,
        "quarantined_paths": quarantined_paths,
        "asset_manifest_sha256": source_hashes["asset_manifest"],
        "asset_index_sha256": source_hashes["asset_index"],
        "duplicates_report_sha256": source_hashes["duplicates_report"],
        "quarantine_manifest_sha256": source_hashes[
            "asset_runtime_quarantine_manifest"
        ],
        "validation_report_sha256": source_hashes[
            "asset_runtime_validation_report"
        ],
        "audit_log_sha256": source_hashes["asset_runtime_audit_log"],
    }


def _asset_rows(
    *,
    asset_manifest: dict,
    duplicates_report: dict,
    input_dir: Path,
    scan_run_id: str,
) -> list[dict[str, object]]:
    assets = _list_field(asset_manifest, "assets", "asset_manifest")
    duplicate_digests = {
        _text_field(group, "sha256", "duplicates_report.duplicate_groups")
        for group in _list_field(
            duplicates_report,
            "duplicate_groups",
            "duplicates_report",
        )
        if isinstance(group, dict)
    }
    rows = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("local asset sqlite asset record is malformed")
        relative_path = _text_field(asset, "relative_path", "asset_manifest.assets")
        digest = _text_field(asset, "sha256", "asset_manifest.assets")
        asset_id = _asset_id(relative_path, digest)
        duplicate_group_id = (
            _duplicate_group_id(digest) if digest in duplicate_digests else None
        )
        rows.append(
            {
                "asset_id": asset_id,
                "scan_run_id": scan_run_id,
                "relative_path": relative_path,
                "path": _joined_path_text(input_dir, relative_path),
                "file_name": _text_field(asset, "file_name", "asset_manifest.assets"),
                "extension": _text_field(asset, "extension", "asset_manifest.assets"),
                "media_class": _text_field(
                    asset,
                    "asset_type",
                    "asset_manifest.assets",
                ),
                "size_bytes": _int_field(
                    asset,
                    "size_bytes",
                    "asset_manifest.assets",
                ),
                "sha256": digest,
                "is_duplicate": 1 if duplicate_group_id is not None else 0,
                "duplicate_group_id": duplicate_group_id,
                "is_quarantined": 0,
                "quarantine_reason": None,
                "content_indexed": 0,
                "raw_content_copied": 0,
            }
        )
    return sorted(rows, key=lambda row: str(row["relative_path"]))


def _duplicate_group_rows(
    *,
    assets: list[dict[str, object]],
    duplicates_report: dict,
    scan_run_id: str,
) -> list[dict[str, object]]:
    assets_by_digest: dict[str, list[dict[str, object]]] = {}
    for asset in assets:
        assets_by_digest.setdefault(str(asset["sha256"]), []).append(asset)

    rows = []
    for group in _list_field(
        duplicates_report,
        "duplicate_groups",
        "duplicates_report",
    ):
        if not isinstance(group, dict):
            raise ValueError("local asset sqlite duplicate group is malformed")
        digest = _text_field(group, "sha256", "duplicates_report.duplicate_groups")
        digest_assets = assets_by_digest.get(digest, [])
        rows.append(
            {
                "duplicate_group_id": _duplicate_group_id(digest),
                "scan_run_id": scan_run_id,
                "sha256": digest,
                "asset_count": len(digest_assets),
                "total_size_bytes": sum(
                    int(asset["size_bytes"]) for asset in digest_assets
                ),
            }
        )
    return sorted(rows, key=lambda row: str(row["sha256"]))


def _quarantine_event_rows(
    *,
    quarantine_manifest: dict,
    input_dir: Path,
    scan_run_id: str,
) -> list[dict[str, object]]:
    rows = []
    for item in _list_field(quarantine_manifest, "items", "quarantine_manifest"):
        if not isinstance(item, dict):
            raise ValueError("local asset sqlite quarantine item is malformed")
        relative_path = _text_field(item, "relative_path", "quarantine_manifest.items")
        reason = _text_field(item, "reason", "quarantine_manifest.items")
        rows.append(
            {
                "quarantine_event_id": _quarantine_event_id(relative_path, reason),
                "scan_run_id": scan_run_id,
                "relative_path": relative_path,
                "path": _joined_path_text(input_dir, relative_path),
                "reason": reason,
                "severity": "soft_quarantine",
                "raw_content_copied": 0,
            }
        )
    return sorted(
        rows,
        key=lambda row: (str(row["relative_path"]), str(row["reason"])),
    )


def _index_metadata(
    *,
    scan_run_id: str,
    source_artifacts: list[dict[str, object]],
) -> dict[str, str]:
    return {
        "authority": _AUTHORITY,
        "content_indexed": "false",
        "deterministic_insert_order": "true",
        "execution_capability": _EXECUTION_CAPABILITY,
        "global_database_state": "not_used",
        "raw_content_copied": "false",
        "scan_run_id": scan_run_id,
        "schema_version": LOCAL_ASSET_SQLITE_SCHEMA_VERSION,
        "source_artifacts_sha256": sha256_canonical_json(
            [
                {
                    "artifact_role": artifact["artifact_role"],
                    "sha256": artifact["sha256"],
                }
                for artifact in source_artifacts
            ]
        ),
    }


def _write_sqlite_database(
    *,
    database_path: Path,
    scan: dict[str, object],
    assets: list[dict[str, object]],
    duplicate_groups: list[dict[str, object]],
    quarantine_events: list[dict[str, object]],
    source_artifacts: list[dict[str, object]],
    metadata: dict[str, str],
) -> None:
    _reserve_output_file(database_path)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(database_path))
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        for statement in _CREATE_TABLE_SQL:
            connection.execute(statement)
        for statement in _CREATE_INDEX_SQL:
            connection.execute(statement)
        connection.execute(
            """
            INSERT INTO scan_runs (
              scan_run_id, project_id, input_dir, output_dir, recursive,
              include_hidden, files_scanned, bytes_scanned, duplicate_groups,
              quarantined_paths, asset_manifest_sha256, asset_index_sha256,
              duplicates_report_sha256, quarantine_manifest_sha256,
              validation_report_sha256, audit_log_sha256
            ) VALUES (
              :scan_run_id, :project_id, :input_dir, :output_dir, :recursive,
              :include_hidden, :files_scanned, :bytes_scanned, :duplicate_groups,
              :quarantined_paths, :asset_manifest_sha256, :asset_index_sha256,
              :duplicates_report_sha256, :quarantine_manifest_sha256,
              :validation_report_sha256, :audit_log_sha256
            )
            """,
            scan,
        )
        connection.executemany(
            """
            INSERT INTO assets (
              asset_id, scan_run_id, relative_path, path, file_name, extension,
              media_class, size_bytes, sha256, is_duplicate, duplicate_group_id,
              is_quarantined, quarantine_reason, content_indexed, raw_content_copied
            ) VALUES (
              :asset_id, :scan_run_id, :relative_path, :path, :file_name, :extension,
              :media_class, :size_bytes, :sha256, :is_duplicate, :duplicate_group_id,
              :is_quarantined, :quarantine_reason, :content_indexed,
              :raw_content_copied
            )
            """,
            assets,
        )
        connection.executemany(
            """
            INSERT INTO duplicate_groups (
              duplicate_group_id, scan_run_id, sha256, asset_count, total_size_bytes
            ) VALUES (
              :duplicate_group_id, :scan_run_id, :sha256, :asset_count,
              :total_size_bytes
            )
            """,
            duplicate_groups,
        )
        connection.executemany(
            """
            INSERT INTO quarantine_events (
              quarantine_event_id, scan_run_id, relative_path, path, reason, severity,
              raw_content_copied
            ) VALUES (
              :quarantine_event_id, :scan_run_id, :relative_path, :path, :reason,
              :severity, :raw_content_copied
            )
            """,
            quarantine_events,
        )
        connection.executemany(
            """
            INSERT INTO artifact_sources (artifact_role, path, sha256, size_bytes)
            VALUES (:artifact_role, :path, :sha256, :size_bytes)
            """,
            [
                {
                    "artifact_role": artifact["artifact_role"],
                    "path": artifact["path"],
                    "sha256": artifact["sha256"],
                    "size_bytes": artifact["size_bytes"],
                }
                for artifact in source_artifacts
            ],
        )
        connection.executemany(
            "INSERT INTO index_metadata (key, value) VALUES (?, ?)",
            [(key, metadata[key]) for key in sorted(metadata)],
        )
        connection.commit()
    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise ValueError("local asset sqlite index build failed") from error
    finally:
        if connection is not None:
            connection.close()


def _manifest_payload(
    *,
    database_path: Path,
    manifest_path: Path,
    query_summary_path: Path,
    scan_run_id: str,
    row_counts: dict[str, int],
    source_artifacts: list[dict[str, object]],
    database_sha256: str,
    database_size_bytes: int,
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "database_path": database_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "query_summary_path": query_summary_path.as_posix(),
        "schema_version": LOCAL_ASSET_SQLITE_SCHEMA_VERSION,
        "schema_tables": list(LOCAL_ASSET_SQLITE_SCHEMA_TABLES),
        "scan_run_id": scan_run_id,
        "row_counts": row_counts,
        "source_artifacts": source_artifacts,
        "database_sha256": database_sha256,
        "database_size_bytes": database_size_bytes,
        "deterministic_insert_order": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _query_summary_markdown(
    *,
    database_path: Path,
    scan: dict[str, object],
    row_counts: dict[str, int],
    assets: list[dict[str, object]],
    duplicate_groups: list[dict[str, object]],
    quarantine_events: list[dict[str, object]],
) -> str:
    extension_counts: dict[str, int] = {}
    media_class_counts: dict[str, int] = {}
    for asset in assets:
        extension = str(asset["extension"]) or "[none]"
        media_class = str(asset["media_class"])
        extension_counts[extension] = extension_counts.get(extension, 0) + 1
        media_class_counts[media_class] = media_class_counts.get(media_class, 0) + 1

    lines = [
        "# Local Asset SQLite Query Summary",
        "",
        f"- Scan run ID: `{scan['scan_run_id']}`",
        f"- Database path: `{database_path.as_posix()}`",
        f"- Files scanned: {scan['files_scanned']}",
        f"- Bytes scanned: {scan['bytes_scanned']}",
        f"- Duplicate group count: {len(duplicate_groups)}",
        f"- Quarantined path count: {len(quarantine_events)}",
        "",
        "## Table Row Counts",
        "",
        "| Table | Rows |",
        "| --- | ---: |",
    ]
    for table in LOCAL_ASSET_SQLITE_SCHEMA_TABLES:
        lines.append(f"| `{table}` | {row_counts[table]} |")

    lines.extend(
        [
            "",
            "## Top Extensions By Count",
            "",
            "| Extension | Count |",
            "| --- | ---: |",
        ]
    )
    for extension, count in sorted(
        extension_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]:
        lines.append(f"| `{extension}` | {count} |")
    if not extension_counts:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Media Class Counts",
            "",
            "| Media class | Count |",
            "| --- | ---: |",
        ]
    )
    for media_class, count in sorted(media_class_counts.items()):
        lines.append(f"| `{media_class}` | {count} |")
    if not media_class_counts:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Safe Example Queries",
            "",
            "```sql",
            "SELECT COUNT(*) AS asset_count FROM assets;",
            "",
            "SELECT duplicate_group_id, asset_count, total_size_bytes",
            "FROM duplicate_groups",
            "ORDER BY asset_count DESC, duplicate_group_id;",
            "",
            "SELECT relative_path, reason, severity",
            "FROM quarantine_events",
            "ORDER BY relative_path, reason;",
            "",
            "SELECT relative_path, media_class, size_bytes",
            "FROM assets",
            "WHERE extension = '.png'",
            "ORDER BY relative_path;",
            "",
            "SELECT relative_path, extension, size_bytes",
            "FROM assets",
            "ORDER BY size_bytes DESC, relative_path",
            "LIMIT 20;",
            "",
            "SELECT media_class, COUNT(*) AS asset_count, SUM(size_bytes) AS total_bytes",
            "FROM assets",
            "GROUP BY media_class",
            "ORDER BY asset_count DESC, media_class;",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _connect_readonly(database_path: Path) -> sqlite3.Connection:
    uri = "file:" + quote(database_path.resolve(strict=True).as_posix()) + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _reserve_output_file(path: Path) -> None:
    try:
        with Path(path).open("xb"):
            pass
    except FileExistsError as error:
        raise ValueError(
            "local asset sqlite index output already exists: " + Path(path).name
        ) from error


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    try:
        with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
            json.dump(payload, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(
            "local asset sqlite index output already exists: " + Path(path).name
        ) from error


def _write_text_exclusive(path: Path, content: str) -> None:
    try:
        with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(content)
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(
            "local asset sqlite index output already exists: " + Path(path).name
        ) from error


def _scan_run_id(
    *,
    asset_manifest_sha256: str,
    input_dir: str,
    output_dir: str,
    project_id: object,
    recursive: bool,
    include_hidden: bool,
) -> str:
    digest = sha256_canonical_json(
        {
            "asset_manifest_sha256": asset_manifest_sha256,
            "include_hidden": include_hidden,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "project_id": project_id,
            "recursive": recursive,
            "schema_version": LOCAL_ASSET_SQLITE_SCHEMA_VERSION,
        }
    )
    return "scan_run_" + digest[:24]


def _asset_id(relative_path: str, digest: str) -> str:
    return "asset_" + sha256(f"{relative_path}\0{digest}".encode("utf-8")).hexdigest()[
        :16
    ]


def _duplicate_group_id(digest: str) -> str:
    return "duplicate_group_" + digest[:16]


def _quarantine_event_id(relative_path: str, reason: str) -> str:
    return "quarantine_event_" + sha256(
        f"{relative_path}\0{reason}".encode("utf-8")
    ).hexdigest()[:16]


def _joined_path_text(input_dir: Path, relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("local asset sqlite relative path is malformed")
    return (Path(input_dir) / path).as_posix()


def _dict_field(payload: dict, field_name: str, source: str) -> dict:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError("local asset sqlite source field is malformed: " + source)
    return value


def _list_field(payload: dict, field_name: str, source: str) -> list:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError("local asset sqlite source field is malformed: " + source)
    return value


def _text_field(payload: dict, field_name: str, source: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise ValueError("local asset sqlite source field is malformed: " + source)
    return value


def _int_field(payload: dict, field_name: str, source: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("local asset sqlite source field is malformed: " + source)
    return value


def _bool_field(payload: dict, field_name: str, source: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError("local asset sqlite source field is malformed: " + source)
    return value
