"""Shared helpers for the SEOS Creative Pipeline V3 surface."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

SCHEMA_VERSION = "seos_creative_pipeline_v3"
PRODUCT_STATE = "SEOS_CREATIVE_PIPELINE_REAL_WORLD_EXCELLENCE_READY"
WAITING_STATE = "EXTERNAL_ADOPTION_LOOP_ACTIVE_WAITING_FOR_REAL_USERS"
ADAPTER_NAMES = (
    "comfyui",
    "blender",
    "houdini",
    "zbrush",
    "unreal",
    "davinci",
    "after_effects",
)
ADAPTER_LEVELS = (
    "LEVEL_0_REGISTRY_ONLY",
    "LEVEL_1_DRY_RUN",
    "LEVEL_2_SMOKE_TEST",
    "LEVEL_3_READ_ONLY_INSPECT",
    "LEVEL_4_STAGED_OUTPUT",
    "LEVEL_5_APPROVED_EXECUTION",
)
ERROR_CODES = (
    "ENV_NOT_FOUND",
    "LICENSE_BLOCKED",
    "FILE_MISSING",
    "ARCHIVE_PART_MISSING",
    "ADAPTER_UNSUPPORTED",
    "VALIDATION_FAILED",
    "PERMISSION_DENIED",
    "USER_APPROVAL_REQUIRED",
    "LONG_TASK_BLOCKED",
    "PRIVATE_ASSET_NOT_COMMITTABLE",
    "LOCAL_PATH_LEAK_BLOCKED",
    "LARGE_FILE_BLOCKED",
    "EXTERNAL_ADOPTION_NOT_CONFIRMED",
    "UNSAFE_DESTRUCTIVE_ACTION_BLOCKED",
    "RELEASE_GATE_FAILED",
    "DEMO_ASSET_UNSAFE",
    "QUICKSTART_FAILED",
    "DOCS_INCOMPLETE",
    "HEALTH_METRIC_REGRESSION",
)
LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/",
    "Documents" + "/Codex",
    "files-mentioned" + "-by-the-user",
    "/Desktop/",
)

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def stable_id(prefix: str, *parts: object) -> str:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    safe_prefix = re.sub(r"[^A-Z0-9_]", "_", prefix.upper()).strip("_")
    return f"{safe_prefix}_{digest}"

def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

def partial_sha256(path: Path, *, max_read_bytes: int = 1_048_576) -> str:
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(f"size:{size}\n".encode("utf-8"))
    with path.open("rb") as handle:
        if size <= max_read_bytes:
            digest.update(handle.read())
        else:
            head_size = max_read_bytes // 2
            tail_size = max_read_bytes - head_size
            digest.update(handle.read(head_size))
            handle.seek(max(0, size - tail_size))
            digest.update(handle.read(tail_size))
    return "sha256:" + digest.hexdigest()

def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name

def sanitize_path(value: object) -> str:
    text = str(value)
    if any(marker in text for marker in LOCAL_PATH_MARKERS) or text.startswith("/"):
        return f"<local-path:{Path(text).name}>"
    return text

def run_git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=repo_root(), check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return "UNKNOWN"
    return completed.stdout.strip()

def metadata(kind: str, identifier: str, *, status: str = "READY") -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "id": identifier,
        "kind": kind,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source": "seos_creative_pipeline_v3",
        "scope": "local_first_creative_pipeline",
        "status": status,
        "validation": {"mode": "repository_static_and_fixture_backed"},
        "evidence": [],
        "residual_risk": "External adoption and DCC license availability require real-world confirmation.",
        "public": True,
        "private": False,
    }
