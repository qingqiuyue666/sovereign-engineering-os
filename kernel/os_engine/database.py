"""SQLite WAL brain for the Sovereign OS engine v3 core."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from kernel.os_engine.schema_version import SCHEMA_CONTENT_HASH, SCHEMA_STATEMENTS, SCHEMA_VERSION

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

SECRET_KEY_PATTERN = re.compile(
    r"(?i)(^env$|\.env|api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
)
SECRET_PATH_NAMES = frozenset({".env", ".env.local", ".envrc"})


class DatabaseError(RuntimeError):
    """Base exception for durable OS database failures."""


class DatabasePathError(DatabaseError):
    """Raised when the configured database path escapes the allowed root."""


class UnsafePayloadError(DatabaseError):
    """Raised when a payload contains secret-like or raw environment material."""


@dataclass(frozen=True, slots=True)
class DatabaseSummary:
    root: str
    db_path: str
    schema_version: int
    schema_hash: str
    journal_mode: str
    foreign_keys: bool
    busy_timeout_ms: int
    tables: tuple[str, ...]

    @property
    def content_hash(self) -> str:
        return stable_content_hash(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["content_hash"] = self.content_hash
        return dict(sorted(payload.items()))


class OSDatabase:
    """Small deterministic SQLite wrapper with WAL and root isolation."""

    def __init__(self, *, root: Path, db_path: Path, busy_timeout_ms: int = 5000) -> None:
        self.root = _validate_root(root)
        self.db_path = validate_path_within_root(root=self.root, path=db_path)
        if busy_timeout_ms <= 0:
            raise DatabaseError("busy_timeout_ms must be positive")
        self.busy_timeout_ms = busy_timeout_ms

    def initialize(self) -> DatabaseSummary:
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_version(version, applied_at, content_hash)
                VALUES (?, ?, ?)
                """,
                (SCHEMA_VERSION, "1970-01-01T00:00:00+00:00", SCHEMA_CONTENT_HASH),
            )
            connection.commit()
            tables = tuple(
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                ).fetchall()
            )
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
            busy_timeout = int(connection.execute("PRAGMA busy_timeout").fetchone()[0])
        return DatabaseSummary(
            root=str(self.root),
            db_path=str(self.db_path),
            schema_version=SCHEMA_VERSION,
            schema_hash=SCHEMA_CONTENT_HASH,
            journal_mode=journal_mode,
            foreign_keys=foreign_keys,
            busy_timeout_ms=busy_timeout,
            tables=tables,
        )

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path))
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def schema_hash(self) -> str:
        return SCHEMA_CONTENT_HASH

    def table_names(self) -> tuple[str, ...]:
        self.initialize()
        with self.connect() as connection:
            return tuple(
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                ).fetchall()
            )


def initialize_database(*, root: Path, db_path: Path, busy_timeout_ms: int = 5000) -> DatabaseSummary:
    return OSDatabase(root=root, db_path=db_path, busy_timeout_ms=busy_timeout_ms).initialize()


def canonical_json(payload: JsonValue | dict[str, Any] | list[Any]) -> str:
    validate_no_secret_like(payload)
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise UnsafePayloadError("payload must be deterministic JSON") from exc


def stable_content_hash(payload: JsonValue | dict[str, Any] | list[Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def validate_no_secret_like(payload: Any, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            if SECRET_KEY_PATTERN.search(key_text):
                raise UnsafePayloadError(f"secret-like payload key rejected: {'.'.join(path + (key_text,))}")
            validate_no_secret_like(value, path=path + (key_text,))
        return
    if isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            validate_no_secret_like(item, path=path + (str(index),))
        return
    if isinstance(payload, str):
        if any(part in SECRET_PATH_NAMES for part in Path(payload).parts):
            raise UnsafePayloadError("secret-like path material rejected")
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(payload):
                raise UnsafePayloadError("secret-like payload value rejected")
        return
    if payload is None or isinstance(payload, (bool, int, float)):
        return
    raise UnsafePayloadError(f"unsupported payload type: {type(payload).__name__}")


def validate_path_within_root(*, root: Path, path: Path) -> Path:
    resolved_root = _validate_root(root)
    raw_path = path.expanduser()
    if not str(raw_path):
        raise DatabasePathError("database path is required")
    if raw_path.is_symlink():
        raise DatabasePathError(f"database path cannot be a symlink: {raw_path}")
    resolved_path = raw_path.resolve(strict=False)
    if not resolved_path.is_relative_to(resolved_root):
        raise DatabasePathError(f"database path escapes configured root: {resolved_path}")
    if any(part in SECRET_PATH_NAMES for part in resolved_path.parts):
        raise DatabasePathError("database path cannot point at secret-like files")
    return resolved_path


def _validate_root(root: Path) -> Path:
    raw_root = root.expanduser()
    if not str(raw_root):
        raise DatabasePathError("root is required")
    if raw_root.exists() and raw_root.is_symlink():
        raise DatabasePathError(f"root cannot be a symlink: {raw_root}")
    if raw_root.exists() and not raw_root.is_dir():
        raise DatabasePathError(f"root must be a directory: {raw_root}")
    resolved = raw_root.resolve(strict=False)
    if any(part in SECRET_PATH_NAMES for part in resolved.parts):
        raise DatabasePathError("root cannot be secret-like")
    return resolved
