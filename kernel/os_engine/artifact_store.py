"""SQLite-backed local artifact metadata catalog."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Iterator

CHUNK_SIZE = 4 * 1024 * 1024
DEFAULT_STORAGE_ROOT = Path.home() / ".sovereign_engineering_os" / "artifacts"
HEAVY_ARTIFACT_EXTENSIONS = frozenset(
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
SECRET_PATH_PATTERN = re.compile(r"(?i)(^\.env$|credential|id_rsa|id_dsa|id_ed25519|secret|token)")


class ArtifactStoreError(RuntimeError):
    """Base exception for artifact catalog failures."""


class ArtifactIsolationError(ArtifactStoreError):
    """Raised when an artifact attempts to enter git-tracked storage."""


class ArtifactValidationError(ArtifactStoreError):
    """Raised when artifact metadata fails policy validation."""


class ArtifactType(StrEnum):
    AUDIT_JSON = "audit_json"
    AUDIT_MD = "audit_md"
    RENDER_FRAME = "render_frame"
    PREVIEW_IMAGE = "preview_image"
    PREVIEW_VIDEO = "preview_video"
    CONTEXT_PACKET = "context_packet"
    ASSET_INDEX = "asset_index"
    CHECKSUM_MANIFEST = "checksum_manifest"
    FAILURE_BUNDLE = "failure_bundle"
    DAVINCI_HANDOFF = "davinci_handoff"
    COMFYUI_OUTPUT = "comfyui_output"
    HFX_PROOF_RESULT = "hfx_proof_result"


class ReviewStatus(StrEnum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    PUBLISH_READY = "publish_ready"


class QuarantineStatus(StrEnum):
    CLEAN = "clean"
    QUARANTINED = "quarantined"
    RELEASED = "released"


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    job_id: str
    local_path: Path
    sha256: str
    size_bytes: int
    artifact_type: str
    review_status: str
    quarantine_status: str
    quarantine_reason: str | None
    local_only: bool
    safe_for_github: bool
    path_policy: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ArtifactValidationError("artifact_id is required")
        if not self.job_id:
            raise ArtifactValidationError("job_id is required")
        if not str(self.local_path):
            raise ArtifactValidationError("local_path is required")
        ArtifactType(self.artifact_type)
        ReviewStatus(self.review_status)
        QuarantineStatus(self.quarantine_status)
        if self.quarantine_status == QuarantineStatus.QUARANTINED.value and not self.quarantine_reason:
            raise ArtifactValidationError("quarantine requires reason")
        if self.local_only and self.review_status == ReviewStatus.PUBLISH_READY.value:
            raise ArtifactValidationError("local_only artifacts cannot claim publish-ready status")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ArtifactRecord":
        return cls(
            artifact_id=str(row["artifact_id"]),
            job_id=str(row["job_id"]),
            local_path=Path(str(row["local_path"])),
            sha256=str(row["sha256"]),
            size_bytes=int(row["size_bytes"]),
            artifact_type=str(row["artifact_type"]) if "artifact_type" in row.keys() else ArtifactType.AUDIT_JSON.value,
            review_status=str(row["review_status"]),
            quarantine_status=str(row["quarantine_status"]),
            quarantine_reason=(
                str(row["quarantine_reason"])
                if "quarantine_reason" in row.keys() and row["quarantine_reason"] is not None
                else None
            ),
            local_only=bool(row["local_only"]) if "local_only" in row.keys() else True,
            safe_for_github=bool(row["safe_for_github"]) if "safe_for_github" in row.keys() else False,
            path_policy=str(row["path_policy"]) if "path_policy" in row.keys() else "absolute_local_only",
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def to_dict(self) -> dict[str, str | int]:
        payload: dict[str, str | int] = {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "job_id": self.job_id,
            "local_path": str(self.local_path),
            "local_only": int(self.local_only),
            "path_policy": self.path_policy,
            "quarantine_reason": self.quarantine_reason or "",
            "quarantine_status": self.quarantine_status,
            "review_status": self.review_status,
            "safe_for_github": int(self.safe_for_github),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        return dict(sorted(payload.items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class ArtifactStore:
    """Metadata-only SQLite catalog with hard local artifact isolation."""

    def __init__(
        self,
        *,
        db_path: Path,
        artifact_root: Path,
        repo_root: Path | None = None,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        self.db_path = db_path.expanduser().resolve()
        self.artifact_root = artifact_root.expanduser().resolve()
        self.repo_root = repo_root.expanduser().resolve() if repo_root is not None else None
        self.chunk_size = chunk_size

    @classmethod
    def default(cls, repo_root: Path | None = None) -> "ArtifactStore":
        root = DEFAULT_STORAGE_ROOT
        return cls(db_path=root / "artifact_catalog.sqlite3", artifact_root=root, repo_root=repo_root)

    def initialize(self) -> None:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    local_path TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    artifact_type TEXT NOT NULL DEFAULT 'audit_json',
                    review_status TEXT NOT NULL,
                    quarantine_status TEXT NOT NULL,
                    quarantine_reason TEXT,
                    local_only INTEGER NOT NULL DEFAULT 1,
                    safe_for_github INTEGER NOT NULL DEFAULT 0,
                    path_policy TEXT NOT NULL DEFAULT 'absolute_local_only',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_schema_columns(connection)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts(job_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256 ON artifacts(sha256)")

    def register_artifact(
        self,
        *,
        job_id: str,
        local_path: Path,
        artifact_type: ArtifactType | str | None = None,
        review_status: ReviewStatus = ReviewStatus.NEW,
        quarantine_status: QuarantineStatus = QuarantineStatus.CLEAN,
        quarantine_reason: str | None = None,
        local_only: bool = True,
        safe_for_github: bool | None = None,
    ) -> ArtifactRecord:
        self.initialize()
        if not job_id:
            raise ArtifactValidationError("job_id is required")
        artifact_type_value = ArtifactType(artifact_type or infer_artifact_type(local_path)).value
        ReviewStatus(review_status)
        QuarantineStatus(quarantine_status)
        if quarantine_status == QuarantineStatus.QUARANTINED and not quarantine_reason:
            raise ArtifactValidationError("quarantine requires reason")
        if local_only and review_status == ReviewStatus.PUBLISH_READY:
            raise ArtifactValidationError("local_only artifacts cannot claim publish-ready status")
        path = self._validate_local_path(local_path)
        if not path.is_file():
            raise ArtifactStoreError(f"artifact path is not a file: {path}")
        sha256 = self.sha256_file(path)
        size_bytes = path.stat().st_size
        is_heavy_or_binary = _compound_suffix(path).lower() in HEAVY_ARTIFACT_EXTENSIONS or size_bytes > 10 * 1024 * 1024
        github_safe = bool(safe_for_github) if safe_for_github is not None else not is_heavy_or_binary
        now = datetime.now(UTC).isoformat()
        artifact_id = stable_artifact_id(job_id=job_id, local_path=path, sha256=sha256)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT artifact_id, created_at FROM artifacts WHERE local_path = ?",
                (str(path),),
            ).fetchone()
            if existing is not None:
                artifact_id = str(existing["artifact_id"])
                created_at = str(existing["created_at"])
            else:
                created_at = now
            connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id,
                    job_id,
                    local_path,
                    sha256,
                    size_bytes,
                    artifact_type,
                    review_status,
                    quarantine_status,
                    quarantine_reason,
                    local_only,
                    safe_for_github,
                    path_policy,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    job_id = excluded.job_id,
                    local_path = excluded.local_path,
                    sha256 = excluded.sha256,
                    size_bytes = excluded.size_bytes,
                    artifact_type = excluded.artifact_type,
                    review_status = excluded.review_status,
                    quarantine_status = excluded.quarantine_status,
                    quarantine_reason = excluded.quarantine_reason,
                    local_only = excluded.local_only,
                    safe_for_github = excluded.safe_for_github,
                    path_policy = excluded.path_policy,
                    updated_at = excluded.updated_at
                """,
                (
                    artifact_id,
                    job_id,
                    str(path),
                    sha256,
                    size_bytes,
                    artifact_type_value,
                    review_status.value,
                    quarantine_status.value,
                    quarantine_reason,
                    int(local_only),
                    int(github_safe),
                    "absolute_local_only",
                    created_at,
                    now,
                ),
            )
        record = self.get_artifact(artifact_id)
        if record is None:
            raise ArtifactStoreError("artifact registration failed")
        return record

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        return ArtifactRecord.from_row(row) if row is not None else None

    def list_artifacts(
        self,
        *,
        job_id: str | None = None,
        include_quarantined: bool = True,
    ) -> list[ArtifactRecord]:
        self.initialize()
        query = "SELECT * FROM artifacts"
        clauses: list[str] = []
        args: list[str] = []
        if job_id is not None:
            clauses.append("job_id = ?")
            args.append(job_id)
        if not include_quarantined:
            clauses.append("quarantine_status != ?")
            args.append(QuarantineStatus.QUARANTINED.value)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, args).fetchall()
        return [ArtifactRecord.from_row(row) for row in rows]

    def update_review_status(self, artifact_id: str, status: ReviewStatus) -> None:
        self._update_status(artifact_id, "review_status", status.value)

    def update_quarantine_status(self, artifact_id: str, status: QuarantineStatus) -> None:
        self._update_status(artifact_id, "quarantine_status", status.value)

    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(self.chunk_size), b""):
                digest.update(block)
        return digest.hexdigest()

    def _validate_local_path(self, local_path: Path) -> Path:
        if not str(local_path):
            raise ArtifactValidationError("local_path is required")
        raw_path = local_path.expanduser()
        if raw_path.is_symlink():
            raise ArtifactIsolationError(f"artifact symlinks are not accepted: {raw_path}")
        if any(SECRET_PATH_PATTERN.search(part) for part in raw_path.parts):
            raise ArtifactValidationError("secret-like artifact paths are not accepted")
        path = local_path.expanduser().resolve()
        if ".git" in path.parts:
            raise ArtifactIsolationError(f"artifact path cannot enter .git: {path}")
        if self.repo_root is not None and path.is_relative_to(self.repo_root):
            raise ArtifactIsolationError(f"artifact path must stay out of the git worktree: {path}")
        if not path.is_relative_to(self.artifact_root):
            raise ArtifactIsolationError(f"artifact path must stay under local artifact root: {path}")
        if path.suffix.lower() in HEAVY_ARTIFACT_EXTENSIONS and self.repo_root and path.is_relative_to(self.repo_root):
            raise ArtifactIsolationError(f"heavy binary artifact cannot live inside git: {path}")
        return path

    def _update_status(self, artifact_id: str, column: str, value: str) -> None:
        if column not in {"review_status", "quarantine_status"}:
            raise ValueError(f"unsupported status column: {column}")
        self.initialize()
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                f"UPDATE artifacts SET {column} = ?, updated_at = ? WHERE artifact_id = ?",
                (value, now, artifact_id),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _ensure_schema_columns(connection: sqlite3.Connection) -> None:
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(artifacts)").fetchall()}
        additions = {
            "artifact_type": "TEXT NOT NULL DEFAULT 'audit_json'",
            "quarantine_reason": "TEXT",
            "local_only": "INTEGER NOT NULL DEFAULT 1",
            "safe_for_github": "INTEGER NOT NULL DEFAULT 0",
            "path_policy": "TEXT NOT NULL DEFAULT 'absolute_local_only'",
        }
        for column, definition in additions.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE artifacts ADD COLUMN {column} {definition}")


def sha256_file(path: Path, *, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_artifact_manifest(records: Iterable[ArtifactRecord]) -> list[dict[str, str | int]]:
    return [record.to_dict() for record in sorted(records, key=lambda item: item.artifact_id)]


def stable_artifact_id(*, job_id: str, local_path: Path, sha256: str) -> str:
    seed = f"{job_id}\0{local_path.resolve()}\0{sha256}".encode("utf-8")
    return f"artifact_{hashlib.sha256(seed).hexdigest()[:24]}"


def infer_artifact_type(path: Path) -> ArtifactType:
    suffix = _compound_suffix(path).lower()
    name = path.name.lower()
    if "failure" in name or "crash" in name:
        return ArtifactType.FAILURE_BUNDLE
    if "davinci" in name:
        return ArtifactType.DAVINCI_HANDOFF
    if "comfy" in name:
        return ArtifactType.COMFYUI_OUTPUT
    if suffix == ".jsonl":
        return ArtifactType.ASSET_INDEX
    if suffix == ".json":
        return ArtifactType.AUDIT_JSON
    if suffix == ".md":
        return ArtifactType.CONTEXT_PACKET if "context" in str(path).lower() else ArtifactType.AUDIT_MD
    if suffix == ".txt" and "sha256" in name:
        return ArtifactType.CHECKSUM_MANIFEST
    if suffix == ".exr":
        return ArtifactType.RENDER_FRAME
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return ArtifactType.PREVIEW_IMAGE
    if suffix in {".mov", ".mp4"}:
        return ArtifactType.PREVIEW_VIDEO
    if "hfx" in name or suffix in {".hip", ".hiplc", ".hipnc", ".vdb", ".abc", ".usd", ".usda", ".usdc"}:
        return ArtifactType.HFX_PROOF_RESULT
    return ArtifactType.AUDIT_JSON


def _compound_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".bgeo.sc"):
        return ".bgeo.sc"
    return path.suffix.lower()
