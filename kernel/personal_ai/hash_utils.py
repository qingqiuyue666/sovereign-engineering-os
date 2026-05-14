"""Deterministic local hash utilities for Personal AI artifacts."""

from pathlib import Path
import hashlib
import json

__all__ = [
    "canonical_json_bytes",
    "hash_artifact_set",
    "sha256_canonical_json",
    "sha256_file",
    "sha256_text",
]


def sha256_file(path: Path) -> str:
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise ValueError("hash artifact path is missing")
    if not artifact_path.is_file():
        raise ValueError("hash artifact path is not a file")
    return hashlib.sha256(artifact_path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_canonical_json(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def hash_artifact_set(artifact_paths: dict[str, Path]) -> dict[str, str]:
    return {
        artifact_name: sha256_file(Path(artifact_paths[artifact_name]))
        for artifact_name in sorted(artifact_paths)
    }
