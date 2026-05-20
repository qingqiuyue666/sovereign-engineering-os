"""SQLite-backed artifact metadata store for materialized OS assets."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from kernel.os_engine.database import OSDatabase, stable_content_hash, utc_now_iso, validate_no_secret_like

CHUNK_SIZE = 4 * 1024 * 1024
SECRET_PATH_PATTERN = re.compile(r"(?i)(^\.env$|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)")
HEAVY_ARTIFACT_SUFFIXES = frozenset(
    {
        ".abc",
        ".bgeo",
        ".bgeo.sc",
        ".exr",
        ".hip",
        ".hiplc",
        ".hipnc",
        ".mov",
        ".mp4",
        ".usd",
        ".usda",
        ".usdc",
        ".vdb",
    }
)


class SQLiteArtifactStoreError(RuntimeError):
    """Base exception for SQLite artifact store failures."""


class ArtifactPathError(SQLiteArtifactStoreError):
    """Raised when artifact paths escape the configured root."""


class ArtifactValidationError(SQLiteArtifactStoreError):
    """Raised when artifact metadata fails closed."""


class ArtifactType(StrEnum):
    AUDIT_JSON = "audit_json"
    AUDIT_MD = "audit_md"
    RENDER_FRAME = "render_frame"
    PREVIEW_IMAGE = "preview_image"
    PREVIEW_VIDEO = "preview_video"
    EXR_SEQUENCE = "exr_sequence"
    PNG_SEQUENCE = "png_sequence"
    MOV_FILE = "mov_file"
    MP4_FILE = "mp4_file"
    CONTEXT_PACKET = "context_packet"
    ASSET_INDEX = "asset_index"
    CHECKSUM_MANIFEST = "checksum_manifest"
    LICENSE_REPORT = "license_report"
    FAILURE_BUNDLE = "failure_bundle"
    SCREENSHOT = "screenshot"
    DAVINCI_HANDOFF = "davinci_handoff"
    COMFYUI_OUTPUT = "comfyui_output"
    HFX_PROOF_RESULT = "hfx_proof_result"
    MATERIALIZATION_SUMMARY = "materialization_summary"


class ReviewStatus(StrEnum):
    NEW = "new"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISH_READY = "publish_ready"


class QuarantineStatus(StrEnum):
    CLEAN = "clean"
    QUARANTINED = "quarantined"
    RELEASED = "released"


@dataclass(frozen=True, slots=True)
class ArtifactFileValidation:
    local_path: str
    exists: bool
    sha256: str
    size_bytes: int
    checksum_valid: bool
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True, slots=True)
class SQLiteArtifactRecord:
    artifact_id: str
    job_id: str
    artifact_type: str
    local_path: str
    sha256: str
    size_bytes: int
    review_status: str
    quarantine_status: str
    quarantine_reason: str | None
    local_only: bool
    safe_to_publish: bool
    created_at: str
    updated_at: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class SQLiteArtifactStore:
    """Metadata-only local artifact catalog backed by the shared OS database."""

    def __init__(
        self,
        *,
        database: OSDatabase,
        artifact_root: Path,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        self.database = database
        self.artifact_root = _validate_artifact_root(artifact_root)
        if chunk_size <= 0:
            raise ArtifactValidationError("chunk_size must be positive")
        self.chunk_size = chunk_size
        self._closed = False
        self.database.initialize()

    def __enter__(self) -> "SQLiteArtifactStore":
        self._ensure_open()
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        _ = (exc_type, exc, traceback)
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True

    def initialize(self) -> None:
        self._ensure_open()
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.database.initialize()

    def record_artifact(
        self,
        *,
        job_id: str,
        local_path: Path,
        artifact_type: str | ArtifactType,
        review_status: str | ReviewStatus = ReviewStatus.NEW,
        quarantine_status: str | QuarantineStatus = QuarantineStatus.CLEAN,
        quarantine_reason: str | None = None,
        local_only: bool = True,
        safe_to_publish: bool | None = None,
        artifact_id: str | None = None,
    ) -> SQLiteArtifactRecord:
        self._ensure_open()
        self.initialize()
        if not job_id:
            raise ArtifactValidationError("job_id is required")
        artifact_type_value = _artifact_type_value(artifact_type)
        review_status_value = _review_status_value(review_status)
        quarantine_status_value = _quarantine_status_value(quarantine_status)
        if quarantine_status_value == QuarantineStatus.QUARANTINED.value and not quarantine_reason:
            raise ArtifactValidationError("quarantine requires reason")
        path = self._validate_artifact_path(local_path)
        validation = self.validate_artifact_file(path)
        github_safe_default = not _is_large_or_binary(path, validation.size_bytes)
        if safe_to_publish is None:
            safe_value = False if local_only else github_safe_default
        else:
            safe_value = bool(safe_to_publish)
        if local_only and safe_value:
            raise ArtifactValidationError("local_only artifacts cannot be marked safe_to_publish")
        if _is_large_or_binary(path, validation.size_bytes) and safe_value:
            raise ArtifactValidationError("large/binary artifacts are not safe to publish by default")
        now = utc_now_iso()
        artifact_id_value = artifact_id or stable_artifact_id(job_id=job_id, local_path=path, sha256=validation.sha256)
        record_hash = _record_hash(
            artifact_id=artifact_id_value,
            job_id=job_id,
            artifact_type=artifact_type_value,
            local_path=str(path),
            sha256=validation.sha256,
            size_bytes=validation.size_bytes,
            review_status=review_status_value,
            quarantine_status=quarantine_status_value,
            quarantine_reason=quarantine_reason,
            local_only=local_only,
            safe_to_publish=safe_value,
        )
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM artifacts WHERE artifact_id = ?",
                (artifact_id_value,),
            ).fetchone()
            created_at = str(existing["created_at"]) if existing is not None else now
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,
                    job_id,
                    artifact_type,
                    local_path,
                    sha256,
                    size_bytes,
                    review_status,
                    quarantine_status,
                    quarantine_reason,
                    local_only,
                    safe_to_publish,
                    created_at,
                    updated_at,
                    content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    job_id = excluded.job_id,
                    artifact_type = excluded.artifact_type,
                    local_path = excluded.local_path,
                    sha256 = excluded.sha256,
                    size_bytes = excluded.size_bytes,
                    review_status = excluded.review_status,
                    quarantine_status = excluded.quarantine_status,
                    quarantine_reason = excluded.quarantine_reason,
                    local_only = excluded.local_only,
                    safe_to_publish = excluded.safe_to_publish,
                    updated_at = excluded.updated_at,
                    content_hash = excluded.content_hash
                """,
                (
                    artifact_id_value,
                    job_id,
                    artifact_type_value,
                    str(path),
                    validation.sha256,
                    validation.size_bytes,
                    review_status_value,
                    quarantine_status_value,
                    quarantine_reason,
                    int(local_only),
                    int(safe_value),
                    created_at,
                    now,
                    record_hash,
                ),
            )
        record = self.get_artifact(artifact_id_value)
        if record is None:
            raise SQLiteArtifactStoreError("artifact insert failed")
        return record

    def get_artifact(self, artifact_id: str) -> SQLiteArtifactRecord | None:
        self._ensure_open()
        self.initialize()
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        return _record_from_row(row) if row is not None else None

    def list_artifacts(self, *, job_id: str | None = None) -> list[SQLiteArtifactRecord]:
        self._ensure_open()
        self.initialize()
        query = "SELECT * FROM artifacts"
        args: list[str] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            args.append(job_id)
        query += " ORDER BY artifact_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, args).fetchall()
        return [_record_from_row(row) for row in rows]

    def quarantine_artifact(self, artifact_id: str, *, reason: str) -> SQLiteArtifactRecord:
        self._ensure_open()
        if not reason:
            raise ArtifactValidationError("quarantine requires reason")
        validate_no_secret_like({"reason": reason})
        record = self.get_artifact(artifact_id)
        if record is None:
            raise SQLiteArtifactStoreError(f"artifact not found: {artifact_id}")
        return self._update_record(
            record,
            quarantine_status=QuarantineStatus.QUARANTINED.value,
            quarantine_reason=reason,
            safe_to_publish=False,
        )

    def review_artifact(self, artifact_id: str, *, review_status: str | ReviewStatus) -> SQLiteArtifactRecord:
        self._ensure_open()
        status_value = _review_status_value(review_status)
        record = self.get_artifact(artifact_id)
        if record is None:
            raise SQLiteArtifactStoreError(f"artifact not found: {artifact_id}")
        if record.local_only and status_value == ReviewStatus.PUBLISH_READY.value:
            raise ArtifactValidationError("local_only artifacts cannot be publish_ready")
        return self._update_record(record, review_status=status_value)

    def validate_artifact_file(self, local_path: Path, *, expected_sha256: str | None = None) -> ArtifactFileValidation:
        self._ensure_open()
        path = self._validate_artifact_path(local_path)
        if not path.is_file():
            raise SQLiteArtifactStoreError(f"artifact file is missing: {path}")
        sha = sha256_file(path, chunk_size=self.chunk_size)
        size = path.stat().st_size
        checksum_valid = expected_sha256 is None or sha == expected_sha256
        payload = {
            "checksum_valid": checksum_valid,
            "exists": True,
            "local_path": str(path),
            "sha256": sha,
            "size_bytes": size,
        }
        return ArtifactFileValidation(
            local_path=str(path),
            exists=True,
            sha256=sha,
            size_bytes=size,
            checksum_valid=checksum_valid,
            content_hash=stable_content_hash(payload),
        )

    def _update_record(self, record: SQLiteArtifactRecord, **updates: Any) -> SQLiteArtifactRecord:
        payload = record.to_dict()
        payload.update(updates)
        payload["updated_at"] = utc_now_iso()
        payload["content_hash"] = _record_hash(
            artifact_id=str(payload["artifact_id"]),
            job_id=str(payload["job_id"]),
            artifact_type=str(payload["artifact_type"]),
            local_path=str(payload["local_path"]),
            sha256=str(payload["sha256"]),
            size_bytes=int(payload["size_bytes"]),
            review_status=str(payload["review_status"]),
            quarantine_status=str(payload["quarantine_status"]),
            quarantine_reason=payload.get("quarantine_reason"),
            local_only=bool(payload["local_only"]),
            safe_to_publish=bool(payload["safe_to_publish"]),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE artifacts
                SET review_status = ?,
                    quarantine_status = ?,
                    quarantine_reason = ?,
                    safe_to_publish = ?,
                    updated_at = ?,
                    content_hash = ?
                WHERE artifact_id = ?
                """,
                (
                    str(payload["review_status"]),
                    str(payload["quarantine_status"]),
                    payload.get("quarantine_reason"),
                    int(bool(payload["safe_to_publish"])),
                    str(payload["updated_at"]),
                    str(payload["content_hash"]),
                    str(payload["artifact_id"]),
                ),
            )
        updated = self.get_artifact(str(payload["artifact_id"]))
        if updated is None:
            raise SQLiteArtifactStoreError("artifact update failed")
        return updated

    def _validate_artifact_path(self, local_path: Path) -> Path:
        raw_path = local_path.expanduser()
        if raw_path.is_symlink():
            raise ArtifactPathError(f"artifact symlinks are not accepted: {raw_path}")
        if any(SECRET_PATH_PATTERN.search(part) for part in raw_path.parts):
            raise ArtifactValidationError("secret-like artifact path rejected")
        path = raw_path.resolve(strict=False)
        if not path.is_relative_to(self.artifact_root):
            raise ArtifactPathError(f"artifact path escapes artifact root: {path}")
        if ".git" in path.parts:
            raise ArtifactPathError("artifact path cannot enter .git")
        return path

    def _ensure_open(self) -> None:
        if self._closed:
            raise SQLiteArtifactStoreError("sqlite artifact store is closed")


def sha256_file(path: Path, *, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_artifact_id(*, job_id: str, local_path: Path, sha256: str) -> str:
    seed = {"job_id": job_id, "local_path": str(local_path.resolve()), "sha256": sha256}
    return f"artifact_{stable_content_hash(seed)[:24]}"


def _validate_artifact_root(root: Path) -> Path:
    raw_root = root.expanduser()
    if raw_root.exists() and raw_root.is_symlink():
        raise ArtifactPathError(f"artifact root cannot be a symlink: {raw_root}")
    if raw_root.exists() and not raw_root.is_dir():
        raise ArtifactPathError(f"artifact root must be a directory: {raw_root}")
    resolved = raw_root.resolve(strict=False)
    if any(SECRET_PATH_PATTERN.search(part) for part in resolved.parts):
        raise ArtifactValidationError("secret-like artifact root rejected")
    return resolved


def _artifact_type_value(value: str | ArtifactType) -> str:
    try:
        return ArtifactType(value).value
    except ValueError as exc:
        raise ArtifactValidationError(f"unsafe artifact_type rejected: {value}") from exc


def _review_status_value(value: str | ReviewStatus) -> str:
    try:
        return ReviewStatus(value).value
    except ValueError as exc:
        raise ArtifactValidationError(f"unsafe review_status rejected: {value}") from exc


def _quarantine_status_value(value: str | QuarantineStatus) -> str:
    try:
        return QuarantineStatus(value).value
    except ValueError as exc:
        raise ArtifactValidationError(f"unsafe quarantine_status rejected: {value}") from exc


def _compound_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".bgeo.sc"):
        return ".bgeo.sc"
    return path.suffix.lower()


def _is_large_or_binary(path: Path, size_bytes: int) -> bool:
    return _compound_suffix(path) in HEAVY_ARTIFACT_SUFFIXES or size_bytes > 10 * 1024 * 1024


def _record_hash(
    *,
    artifact_id: str,
    job_id: str,
    artifact_type: str,
    local_path: str,
    sha256: str,
    size_bytes: int,
    review_status: str,
    quarantine_status: str,
    quarantine_reason: str | None,
    local_only: bool,
    safe_to_publish: bool,
) -> str:
    return stable_content_hash(
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "job_id": job_id,
            "local_only": local_only,
            "local_path": local_path,
            "quarantine_reason": quarantine_reason or "",
            "quarantine_status": quarantine_status,
            "review_status": review_status,
            "safe_to_publish": safe_to_publish,
            "sha256": sha256,
            "size_bytes": size_bytes,
        }
    )


def _record_from_row(row: Any) -> SQLiteArtifactRecord:
    return SQLiteArtifactRecord(
        artifact_id=str(row["artifact_id"]),
        job_id=str(row["job_id"]),
        artifact_type=str(row["artifact_type"]),
        local_path=str(row["local_path"]),
        sha256=str(row["sha256"]),
        size_bytes=int(row["size_bytes"]),
        review_status=str(row["review_status"]),
        quarantine_status=str(row["quarantine_status"]),
        quarantine_reason=str(row["quarantine_reason"]) if row["quarantine_reason"] is not None else None,
        local_only=bool(row["local_only"]),
        safe_to_publish=bool(row["safe_to_publish"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        content_hash=str(row["content_hash"]),
    )
