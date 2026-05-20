"""Out-of-repository checksum ledger for HFX EXR render artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
import argparse
import hashlib
import json
import os
import re
import sys
import uuid

__all__ = [
    "DEFAULT_SEQUENCE_GLOB",
    "ArtifactLedgerError",
    "ExrFileChecksum",
    "RenderArtifactRecord",
    "RenderDirectoryHash",
    "default_ledger_root",
    "hash_exr_directory",
    "load_latest_render_artifact",
    "record_render_artifact",
]

LEDGER_VERSION: Final[str] = "hfx-render-artifact-ledger-v1"
DEFAULT_SEQUENCE_GLOB: Final[str] = "*.exr"
_EXR_MAGIC: Final[bytes] = b"\x76\x2f\x31\x01"
_MIN_EXR_BYTES: Final[int] = 16
_READ_CHUNK_BYTES: Final[int] = 1024 * 1024
_FRAME_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<frame>\d{4,})(?=\.exr\Z)",
    re.IGNORECASE,
)


class ArtifactLedgerError(RuntimeError):
    """Raised when an EXR directory cannot be hashed or ledgered safely."""


@dataclass(frozen=True, slots=True)
class ExrFileChecksum:
    """Stable checksum metadata for one EXR frame artifact."""

    relative_path: str
    frame_number: int | None
    size_bytes: int
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "frame_number": self.frame_number,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ExrFileChecksum:
        relative_path = _require_string(payload, "relative_path")
        sha256 = _require_string(payload, "sha256")
        size_bytes = _require_int(payload, "size_bytes")
        frame_number_value = payload.get("frame_number")
        frame_number: int | None
        if frame_number_value is None:
            frame_number = None
        elif isinstance(frame_number_value, int):
            frame_number = frame_number_value
        else:
            raise ArtifactLedgerError("frame_number must be an integer or null")
        return cls(
            relative_path=relative_path,
            frame_number=frame_number,
            size_bytes=size_bytes,
            sha256=sha256,
        )


@dataclass(frozen=True, slots=True)
class RenderDirectoryHash:
    """Deterministic hash of the EXR files in one render output directory."""

    exr_directory: Path
    sequence_glob: str
    directory_sha256: str
    files: tuple[ExrFileChecksum, ...]

    @property
    def frame_numbers(self) -> tuple[int, ...]:
        return tuple(
            checksum.frame_number
            for checksum in self.files
            if checksum.frame_number is not None
        )

    @property
    def first_frame(self) -> int | None:
        frame_numbers = self.frame_numbers
        if not frame_numbers:
            return None
        return min(frame_numbers)

    @property
    def last_frame(self) -> int | None:
        frame_numbers = self.frame_numbers
        if not frame_numbers:
            return None
        return max(frame_numbers)

    def hash_material(self) -> dict[str, object]:
        return {
            "files": [checksum.as_dict() for checksum in self.files],
            "sequence_glob": self.sequence_glob,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "directory_sha256": self.directory_sha256,
            "exr_directory": self.exr_directory.as_posix(),
            "files": [checksum.as_dict() for checksum in self.files],
            "first_frame": self.first_frame,
            "frame_count": len(self.files),
            "last_frame": self.last_frame,
            "sequence_glob": self.sequence_glob,
        }


@dataclass(frozen=True, slots=True)
class RenderArtifactRecord:
    """Ledger record consumed by downstream handoff tools."""

    ledger_version: str
    record_id: str
    created_at: str
    exr_directory: Path
    sequence_glob: str
    frame_pattern: str | None
    directory_sha256: str
    files: tuple[ExrFileChecksum, ...]
    metadata: Mapping[str, object]
    ledger_path: Path | None = None

    @property
    def frame_numbers(self) -> tuple[int, ...]:
        return tuple(
            checksum.frame_number
            for checksum in self.files
            if checksum.frame_number is not None
        )

    @property
    def first_frame(self) -> int | None:
        frame_numbers = self.frame_numbers
        if not frame_numbers:
            return None
        return min(frame_numbers)

    @property
    def last_frame(self) -> int | None:
        frame_numbers = self.frame_numbers
        if not frame_numbers:
            return None
        return max(frame_numbers)

    @property
    def frame_count(self) -> int:
        return len(self.files)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "created_at": self.created_at,
            "directory_sha256": self.directory_sha256,
            "exr_directory": self.exr_directory.as_posix(),
            "files": [checksum.as_dict() for checksum in self.files],
            "first_frame": self.first_frame,
            "frame_count": self.frame_count,
            "frame_pattern": self.frame_pattern,
            "last_frame": self.last_frame,
            "ledger_path": self.ledger_path.as_posix() if self.ledger_path else None,
            "ledger_version": self.ledger_version,
            "metadata": _json_safe_mapping(self.metadata),
            "record_id": self.record_id,
            "sequence_glob": self.sequence_glob,
        }
        return payload

    def to_json(self) -> str:
        return _canonical_json(self.as_dict()) + "\n"

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> RenderArtifactRecord:
        version = _require_string(payload, "ledger_version")
        if version != LEDGER_VERSION:
            raise ArtifactLedgerError(f"unsupported ledger version: {version}")
        files_value = payload.get("files")
        if not isinstance(files_value, Sequence) or isinstance(files_value, (str, bytes)):
            raise ArtifactLedgerError("files must be a sequence")
        files = tuple(
            ExrFileChecksum.from_dict(_require_mapping(item, "files item"))
            for item in files_value
        )
        metadata_value = payload.get("metadata", {})
        metadata = dict(_require_mapping(metadata_value, "metadata"))
        ledger_path_value = payload.get("ledger_path")
        ledger_path = (
            Path(ledger_path_value)
            if isinstance(ledger_path_value, str) and ledger_path_value
            else None
        )
        frame_pattern_value = payload.get("frame_pattern")
        frame_pattern = frame_pattern_value if isinstance(frame_pattern_value, str) else None
        return cls(
            ledger_version=version,
            record_id=_require_string(payload, "record_id"),
            created_at=_require_string(payload, "created_at"),
            exr_directory=Path(_require_string(payload, "exr_directory")),
            sequence_glob=_require_string(payload, "sequence_glob"),
            frame_pattern=frame_pattern,
            directory_sha256=_require_string(payload, "directory_sha256"),
            files=files,
            metadata=metadata,
            ledger_path=ledger_path,
        )


def default_ledger_root() -> Path:
    """Return the default ledger root outside ordinary repository tracking."""

    override = os.environ.get("SEOS_HFX_LEDGER_ROOT")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "SovereignEngineeringOS"
            / "hfx_render_ledger"
        )
    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        return Path(state_home).expanduser() / "sovereign-engineering-os" / "hfx_render_ledger"
    return Path.home() / ".local" / "state" / "sovereign-engineering-os" / "hfx_render_ledger"


def hash_exr_directory(
    exr_directory: Path | str,
    *,
    sequence_glob: str = DEFAULT_SEQUENCE_GLOB,
) -> RenderDirectoryHash:
    """Hash every EXR matched by sequence_glob and reject corrupt frame files."""

    directory = Path(exr_directory).expanduser().resolve()
    _validate_sequence_glob(sequence_glob)
    if not directory.exists():
        raise ArtifactLedgerError(f"EXR directory is missing: {directory}")
    if not directory.is_dir():
        raise ArtifactLedgerError(f"EXR path is not a directory: {directory}")
    if directory.is_symlink():
        raise ArtifactLedgerError(f"EXR directory may not be a symlink: {directory}")

    frame_paths = _discover_exr_files(directory, sequence_glob)
    if not frame_paths:
        raise ArtifactLedgerError(f"no EXR files matched {sequence_glob!r} in {directory}")

    checksums = tuple(_checksum_exr_file(directory, path) for path in frame_paths)
    material = {
        "files": [checksum.as_dict() for checksum in checksums],
        "sequence_glob": sequence_glob,
    }
    return RenderDirectoryHash(
        exr_directory=directory,
        sequence_glob=sequence_glob,
        directory_sha256=_sha256_bytes(_canonical_json_bytes(material)),
        files=checksums,
    )


def record_render_artifact(
    exr_directory: Path | str,
    *,
    sequence_glob: str = DEFAULT_SEQUENCE_GLOB,
    frame_pattern: str | None = None,
    metadata: Mapping[str, object] | None = None,
    ledger_root: Path | str | None = None,
) -> RenderArtifactRecord:
    """Hash an EXR directory and persist a private ledger record outside Git."""

    directory_hash = hash_exr_directory(exr_directory, sequence_glob=sequence_glob)
    root = _prepare_ledger_root(ledger_root)
    records_dir = root / "records"
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    record_id = uuid.uuid4().hex
    record_path = records_dir / f"{_ledger_timestamp(created_at)}_{record_id}.json"
    record = RenderArtifactRecord(
        ledger_version=LEDGER_VERSION,
        record_id=record_id,
        created_at=created_at,
        exr_directory=directory_hash.exr_directory,
        sequence_glob=sequence_glob,
        frame_pattern=frame_pattern,
        directory_sha256=directory_hash.directory_sha256,
        files=directory_hash.files,
        metadata=_json_safe_mapping(metadata or {}),
        ledger_path=record_path,
    )

    _write_json_atomic(record_path, record.as_dict())
    _write_json_atomic(root / "latest.json", record.as_dict())
    _append_jsonl_secure(
        root / "index.jsonl",
        {
            "created_at": record.created_at,
            "directory_sha256": record.directory_sha256,
            "exr_directory": record.exr_directory.as_posix(),
            "record_id": record.record_id,
            "record_path": record_path.as_posix(),
        },
    )
    return record


def load_latest_render_artifact(
    *,
    ledger_root: Path | str | None = None,
) -> RenderArtifactRecord:
    """Load the latest private render artifact record."""

    root = _resolve_ledger_root(ledger_root)
    _reject_git_worktree_path(root)
    latest_path = root / "latest.json"
    if latest_path.exists():
        return RenderArtifactRecord.from_dict(_read_json_object(latest_path))

    records_dir = root / "records"
    if not records_dir.exists():
        raise ArtifactLedgerError(f"ledger records directory is missing: {records_dir}")
    candidates = sorted(
        (path for path in records_dir.glob("*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if not candidates:
        raise ArtifactLedgerError(f"ledger contains no render records: {records_dir}")
    return RenderArtifactRecord.from_dict(_read_json_object(candidates[0]))


def _discover_exr_files(directory: Path, sequence_glob: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for path in directory.glob(sequence_glob):
        if path.is_dir():
            continue
        if path.suffix.lower() != ".exr":
            continue
        paths.append(path.resolve())
    return tuple(sorted(paths, key=lambda path: path.relative_to(directory).as_posix()))


def _checksum_exr_file(root: Path, path: Path) -> ExrFileChecksum:
    if path.is_symlink():
        raise ArtifactLedgerError(f"EXR frame may not be a symlink: {path}")
    if not path.is_file():
        raise ArtifactLedgerError(f"EXR frame is not a regular file: {path}")
    stat = path.stat()
    if stat.st_size < _MIN_EXR_BYTES:
        raise ArtifactLedgerError(f"EXR frame is too small to be valid: {path}")
    with path.open("rb") as handle:
        magic = handle.read(len(_EXR_MAGIC))
    if magic != _EXR_MAGIC:
        raise ArtifactLedgerError(f"EXR frame failed magic-byte validation: {path}")

    relative_path = path.relative_to(root).as_posix()
    return ExrFileChecksum(
        relative_path=relative_path,
        frame_number=_frame_number_from_name(path.name),
        size_bytes=stat.st_size,
        sha256=_sha256_file(path),
    )


def _frame_number_from_name(name: str) -> int | None:
    match = _FRAME_NUMBER_RE.search(name)
    if match is None:
        return None
    return int(match.group("frame"))


def _validate_sequence_glob(sequence_glob: str) -> None:
    if not sequence_glob:
        raise ArtifactLedgerError("sequence_glob is required")
    candidate = Path(sequence_glob)
    if candidate.is_absolute():
        raise ArtifactLedgerError("sequence_glob must be relative to the EXR directory")
    if ".." in candidate.parts:
        raise ArtifactLedgerError("sequence_glob may not traverse parent directories")
    if "\x00" in sequence_glob:
        raise ArtifactLedgerError("sequence_glob may not contain NUL bytes")
    if not sequence_glob.lower().endswith(".exr"):
        raise ArtifactLedgerError("sequence_glob must target EXR files")


def _prepare_ledger_root(ledger_root: Path | str | None) -> Path:
    root = _resolve_ledger_root(ledger_root)
    _reject_git_worktree_path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "records").mkdir(parents=True, exist_ok=True)
    _chmod_private_dir(root)
    _chmod_private_dir(root / "records")
    return root


def _resolve_ledger_root(ledger_root: Path | str | None) -> Path:
    root = Path(ledger_root).expanduser() if ledger_root is not None else default_ledger_root()
    return root.resolve()


def _reject_git_worktree_path(path: Path) -> None:
    probe = path if path.exists() else path.parent
    for parent in (probe, *probe.parents):
        git_marker = parent / ".git"
        if git_marker.exists():
            raise ArtifactLedgerError(
                "render artifact ledger root must live outside a Git worktree: "
                f"{path}"
            )


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    if path.exists() and path.is_symlink():
        raise ArtifactLedgerError(f"refusing to overwrite symlink ledger path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_private_dir(path.parent)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _append_jsonl_secure(path: Path, payload: Mapping[str, object]) -> None:
    if path.exists() and path.is_symlink():
        raise ArtifactLedgerError(f"refusing to append to symlink ledger path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_private_dir(path.parent)
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(path, 0o600)
    finally:
        pass


def _read_json_object(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise ArtifactLedgerError(f"refusing to read symlink ledger path: {path}")
    if not path.is_file():
        raise ArtifactLedgerError(f"ledger path is not a file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ArtifactLedgerError(f"ledger payload must be a JSON object: {path}")
    return payload


def _chmod_private_dir(path: Path) -> None:
    try:
        os.chmod(path, 0o700)
    except PermissionError as exc:
        raise ArtifactLedgerError(f"could not secure ledger directory: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_json_bytes(payload: object) -> bytes:
    return _canonical_json(payload).encode("utf-8")


def _json_safe_mapping(payload: Mapping[str, object]) -> dict[str, object]:
    try:
        normalized = json.loads(_canonical_json(dict(payload)))
    except (TypeError, ValueError) as exc:
        raise ArtifactLedgerError("metadata must be canonical JSON serializable") from exc
    if not isinstance(normalized, dict):
        raise ArtifactLedgerError("metadata must normalize to a JSON object")
    return normalized


def _ledger_timestamp(created_at: str) -> str:
    return (
        created_at.replace(":", "-")
        .replace("+", "Z")
        .replace(".", "-")
        .replace("/", "-")
    )


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ArtifactLedgerError(f"{name} must be a JSON object")
    return value


def _require_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ArtifactLedgerError(f"{key} must be a nonempty string")
    return value


def _require_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ArtifactLedgerError(f"{key} must be an integer")
    return value


def _parse_metadata(values: Iterable[str]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise ArtifactLedgerError(f"metadata must be key=value: {value}")
        key, raw = value.split("=", 1)
        if not key:
            raise ArtifactLedgerError("metadata key may not be empty")
        metadata[key] = raw
    return metadata


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hash and ledger an HFX EXR directory.")
    parser.add_argument("exr_directory", help="Directory containing final EXR frames.")
    parser.add_argument("--sequence-glob", default=DEFAULT_SEQUENCE_GLOB)
    parser.add_argument("--frame-pattern", default=None)
    parser.add_argument("--ledger-root", default=None)
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Additional ledger metadata in key=value form.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        record = record_render_artifact(
            args.exr_directory,
            sequence_glob=args.sequence_glob,
            frame_pattern=args.frame_pattern,
            metadata=_parse_metadata(args.metadata),
            ledger_root=args.ledger_root,
        )
    except ArtifactLedgerError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(record.to_json(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
