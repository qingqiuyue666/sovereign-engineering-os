"""SQLite-backed local artifact metadata catalog."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Iterable

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


class ArtifactStoreError(RuntimeError):
    """Base exception for artifact catalog failures."""


class ArtifactIsolationError(ArtifactStoreError):
    """Raised when an artifact attempts to enter git-tracked storage."""


class ReviewStatus(StrEnum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


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
    review_status: str
    quarantine_status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ArtifactRecord":
        return cls(
            artifact_id=str(row["artifact_id"]),
            job_id=str(row["job_id"]),
            local_path=Path(str(row["local_path"])),
            sha256=str(row["sha256"]),
            size_bytes=int(row["size_bytes"]),
            review_status=str(row["review_status"]),
            quarantine_status=str(row["quarantine_status"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def to_dict(self) -> dict[str, str | int]:
        return {
            "artifact_id": self.artifact_id,
            "job_id": self.job_id,
            "local_path": str(self.local_path),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "review_status": self.review_status,
            "quarantine_status": self.quarantine_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


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
                    review_status TEXT NOT NULL,
                    quarantine_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts(job_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256 ON artifacts(sha256)")

    def register_artifact(
        self,
        *,
        job_id: str,
        local_path: Path,
        review_status: ReviewStatus = ReviewStatus.NEW,
        quarantine_status: QuarantineStatus = QuarantineStatus.CLEAN,
    ) -> ArtifactRecord:
        self.initialize()
        path = self._validate_local_path(local_path)
        if not path.is_file():
            raise ArtifactStoreError(f"artifact path is not a file: {path}")
        sha256 = self.sha256_file(path)
        size_bytes = path.stat().st_size
        now = datetime.now(UTC).isoformat()
        artifact_id = f"artifact_{sha256[:16]}_{uuid.uuid4().hex[:12]}"
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
                    review_status,
                    quarantine_status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    job_id = excluded.job_id,
                    local_path = excluded.local_path,
                    sha256 = excluded.sha256,
                    size_bytes = excluded.size_bytes,
                    review_status = excluded.review_status,
                    quarantine_status = excluded.quarantine_status,
                    updated_at = excluded.updated_at
                """,
                (
                    artifact_id,
                    job_id,
                    str(path),
                    sha256,
                    size_bytes,
                    review_status.value,
                    quarantine_status.value,
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection


def sha256_file(path: Path, *, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_artifact_manifest(records: Iterable[ArtifactRecord]) -> list[dict[str, str | int]]:
    return [record.to_dict() for record in records]
