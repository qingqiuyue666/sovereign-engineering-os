"""V12 local task OS foundation."""

from .task_manifest import TaskManifestResult, normalize_task_manifest, validate_task_manifest
from .run_id import canonical_json, deterministic_run_id, digest_payload
from .run_ledger import InMemoryRunLedger

__all__ = [
    "InMemoryRunLedger",
    "TaskManifestResult",
    "canonical_json",
    "deterministic_run_id",
    "digest_payload",
    "normalize_task_manifest",
    "validate_task_manifest",
]
