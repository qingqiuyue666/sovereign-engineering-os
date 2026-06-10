"""Quarantine policy helpers for local asset runtime v1."""

from pathlib import Path
import os

UNSAFE_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}

SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".netrc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}

SECRET_EXTENSIONS = {
    ".asc",
    ".gpg",
    ".key",
    ".kdbx",
    ".p12",
    ".pem",
    ".pfx",
}

SECRET_TOKENS = (
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "password",
    "passwd",
    "private_key",
    "secret",
    "secrets",
    "token",
)

__all__ = [
    "has_hidden_part",
    "is_secret_looking_path",
    "is_unsafe_directory_name",
    "quarantine_record",
    "symlink_quarantine_record",
]


def is_unsafe_directory_name(name: str) -> bool:
    return name.lower() in UNSAFE_DIRECTORY_NAMES


def has_hidden_part(relative_path: Path) -> bool:
    return any(part.startswith(".") for part in relative_path.parts)


def is_secret_looking_path(relative_path: Path) -> bool:
    for part in relative_path.parts:
        lower_part = part.lower()
        normalized_part = lower_part.replace("-", "_")
        if lower_part in SECRET_FILE_NAMES:
            return True
        if any(token in normalized_part for token in SECRET_TOKENS):
            return True
    return relative_path.suffix.lower() in SECRET_EXTENSIONS


def quarantine_record(
    relative_path: Path,
    *,
    reason: str,
    path_type: str,
    detail: str,
) -> dict:
    return {
        "detail": detail,
        "path_type": path_type,
        "reason": reason,
        "relative_path": relative_path.as_posix(),
    }


def symlink_quarantine_record(path: Path, input_root: Path) -> dict:
    relative_path = path.relative_to(input_root)
    link_text = _readlink_text(path)
    target_inside_input = False
    reason = "dangerous_symlink"
    detail = "symlink target is outside input_dir or cannot be resolved"
    try:
        resolved_target = path.resolve(strict=True)
        target_inside_input = _path_is_inside(resolved_target, input_root)
        if target_inside_input:
            reason = "symlink_not_followed"
            detail = "symlink was skipped to keep scanning read-only and non-ambiguous"
    except (OSError, RuntimeError):
        target_inside_input = False

    return {
        "detail": detail,
        "link_text": link_text,
        "path_type": "symlink",
        "reason": reason,
        "relative_path": relative_path.as_posix(),
        "target_inside_input": target_inside_input,
    }


def _readlink_text(path: Path) -> str:
    try:
        return os.readlink(path)
    except OSError:
        return "[unreadable-symlink]"


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=True).relative_to(
            Path(root_path).resolve(strict=True)
        )
    except (OSError, ValueError):
        return False
    return True
