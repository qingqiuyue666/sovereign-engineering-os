"""Real local patch application runtime.

v1 — dry-run patch validation and receipt generation. No actual patch
application. No network. No git push/merge/branch delete. No freeform shell.
"""

from __future__ import annotations

from .patch_runtime import PatchRuntime
from .patch_request import PatchRequest
from .patch_allowlist import PatchAllowlist
from .patch_preflight import PatchPreflight
from .patch_receipt import PatchReceipt, PatchFailureReceipt, produce_patch_receipt, produce_patch_failure_receipt
from .patch_rollback import PatchRollback
from .patch_canonical_hash import PatchCanonicalHash
from .patch_security import PatchSecurity

__all__ = [
    "PatchRuntime",
    "PatchRequest",
    "PatchAllowlist",
    "PatchPreflight",
    "PatchReceipt",
    "PatchFailureReceipt",
    "produce_patch_receipt",
    "produce_patch_failure_receipt",
    "PatchRollback",
    "PatchCanonicalHash",
    "PatchSecurity",
]
