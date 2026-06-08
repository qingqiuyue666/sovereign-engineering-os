"""Path containment guards for controlled execution."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


class PathGuardError(ValueError):
    pass


def resolve_output_root(output_root: str | Path) -> Path:
    return Path(output_root).expanduser().resolve()


def assert_within_root(path: str | Path, root: str | Path) -> Path:
    root_path = resolve_output_root(root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise PathGuardError("path_outside_allowed_output_root") from exc
    return resolved


def validate_relative_output_path(relative_path: str) -> str:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise PathGuardError("relative_output_path_required")
    pure = PurePosixPath(relative_path.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise PathGuardError("relative_output_path_escape")
    return pure.as_posix()


def public_output_root_label(output_root: str | Path) -> str:
    name = Path(output_root).name or "output"
    return f"<output-root:{name}>"

