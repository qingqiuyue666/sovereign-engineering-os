"""Narrow shared helpers for minimal controlled runner slices."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_FIXED_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def deterministic_git_safe_env(
    repository_root: Path = REPOSITORY_ROOT,
) -> Mapping[str, str]:
    return MappingProxyType(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(repository_root),
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": _FIXED_PATH,
            "TZ": "UTC",
        }
    )


def bounded_output_metadata(value: object, limit: int) -> dict[str, object]:
    if value is None:
        raw = b""
    elif isinstance(value, bytes):
        raw = value
    else:
        raw = str(value).encode("utf-8", errors="replace")
    bounded = raw[:limit]
    return {
        "digest": "sha256:" + hashlib.sha256(bounded).hexdigest(),
        "truncated": len(raw) > limit,
    }


def canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_head_ref(repository_root: Path = REPOSITORY_ROOT) -> str:
    git_dir = repository_root / ".git"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return "HEAD:unavailable"
    if not head.startswith("ref: "):
        return "HEAD:" + head
    ref_name = head[5:]
    try:
        ref_value = (git_dir / ref_name).read_text(encoding="utf-8").strip()
    except OSError:
        ref_value = "unavailable"
    return "HEAD:" + ref_name + ":" + ref_value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
