"""Deterministic local filesystem intake ledger for Personal AI planning."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import tempfile

__all__ = [
    "LocalFileIntakeResult",
    "build_local_file_intake_ledger",
]


@dataclass(frozen=True)
class LocalFileIntakeResult:
    input_dir: Path
    output_ledger_path: Path
    files_seen: int
    files_recorded: int
    bytes_recorded: int
    skipped_hidden: int
    skipped_symlinks: int
    recursive: bool
    include_hidden: bool


def build_local_file_intake_ledger(
    input_dir: Path,
    output_ledger_path: Path,
    *,
    recursive: bool = False,
    include_hidden: bool = False,
) -> LocalFileIntakeResult:
    input_path = Path(input_dir)
    output_path = Path(output_ledger_path)

    if not input_path.exists():
        raise ValueError("input_dir is missing")
    if not input_path.is_dir():
        raise ValueError("input_dir is not a directory")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_ledger_path parent is missing")
    if _path_is_inside(output_path, input_path):
        raise ValueError("output_ledger_path must be outside input_dir")

    entries, files_seen, skipped_hidden, skipped_symlinks = _collect_entries(
        input_path,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    entries.sort(key=lambda entry: entry["relative_path"])

    _write_jsonl_atomically(output_path, entries)

    return LocalFileIntakeResult(
        input_dir=input_path,
        output_ledger_path=output_path,
        files_seen=files_seen,
        files_recorded=len(entries),
        bytes_recorded=sum(entry["size_bytes"] for entry in entries),
        skipped_hidden=skipped_hidden,
        skipped_symlinks=skipped_symlinks,
        recursive=recursive,
        include_hidden=include_hidden,
    )


def _collect_entries(input_path, *, recursive, include_hidden):
    entries = []
    files_seen = 0
    skipped_hidden = 0
    skipped_symlinks = 0
    pending_dirs = [input_path]

    while pending_dirs:
        current_dir = pending_dirs.pop()
        children = sorted(
            current_dir.iterdir(),
            key=lambda path: path.relative_to(input_path).as_posix(),
        )
        for child in children:
            relative_path = child.relative_to(input_path)
            hidden = _has_hidden_part(relative_path)

            if child.is_symlink():
                files_seen += 1
                skipped_symlinks += 1
                continue

            if child.is_dir():
                if recursive and (include_hidden or not hidden):
                    pending_dirs.append(child)
                continue

            if not child.is_file():
                continue

            files_seen += 1
            if hidden and not include_hidden:
                skipped_hidden += 1
                continue

            file_stat = child.stat()
            size_bytes = file_stat.st_size
            entries.append(
                {
                    "relative_path": relative_path.as_posix(),
                    "size_bytes": size_bytes,
                    "sha256": _sha256_file(child),
                    "modified_time_ns": _modified_time_ns(file_stat),
                }
            )

    return entries, files_seen, skipped_hidden, skipped_symlinks


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = candidate_path.resolve(strict=False)
    resolved_root = root_path.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def _has_hidden_part(relative_path):
    return any(part.startswith(".") for part in relative_path.parts)


def _sha256_file(path):
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _modified_time_ns(file_stat):
    return int(
        getattr(
            file_stat,
            "st_mtime_ns",
            int(file_stat.st_mtime * 1_000_000_000),
        )
    )


def _write_jsonl_atomically(output_path, entries):
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        for entry in entries:
            temporary_file.write(json.dumps(entry, separators=(",", ":")))
            temporary_file.write("\n")
        temporary_file.flush()

    temporary_path.replace(output_path)
