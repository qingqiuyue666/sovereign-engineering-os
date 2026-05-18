"""Patch request — immutable dry-run patch request contract.

Validates patch request structure, target paths, replay linkage, and safety
constraints. Rejects absolute paths, path traversal, forbidden roots, git/main
mutation, network paths, and freeform shell surfaces.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


FORBIDDEN_ROOTS = frozenset({"/", "/etc", "/proc", "/sys", "/dev", "/boot", "/root"})
FORBIDDEN_PATTERNS = ("..", "~", "$HOME", "${HOME}", "%HOME%")
MAIN_MUTATION_PATTERNS = (
    "git checkout main", "git switch main", "git push",
    "git merge", "git branch -d", "git branch -D",
)
ALLOWED_OPERATIONS = frozenset({"add_file", "update_file", "validate_only"})
FORBIDDEN_OPERATIONS = frozenset({
    "delete_file", "chmod", "shell", "git", "network", "production_apply",
})


def _hash64(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


@dataclass(frozen=True)
class PatchRequest:
    """Immutable patch request with validated target, operation, and safety checks."""

    request_id: str
    patch_id: str
    target_path: str
    patch_content_hash: str
    rollback_bundle_hash: str
    allowlist_ids: List[str]
    test_results_hash: str
    is_dry_run: bool
    is_valid: bool
    canonical_hash: str
    operation: str = "validate_only"
    replay_receipt_hash: str = ""

    @staticmethod
    def create(
        patch_id: str,
        target_path: str,
        patch_content_hash: str,
        rollback_bundle_hash: str,
        *,
        allowlist_ids: List[str] | None = None,
        test_results_hash: str = "",
        is_dry_run: bool = True,
        operation: str = "validate_only",
        replay_receipt_hash: str = "",
    ) -> "PatchRequest":
        if not patch_id.strip():
            raise ValueError("patch_id required")
        if not _hash64(patch_content_hash):
            raise ValueError("patch_content_hash must be 64-char hex sha256")
        if not _hash64(rollback_bundle_hash):
            raise ValueError("rollback_bundle_hash must be 64-char hex sha256")
        if test_results_hash and not _hash64(test_results_hash):
            raise ValueError("test_results_hash must be 64-char hex sha256 when provided")
        if replay_receipt_hash and not _hash64(replay_receipt_hash):
            raise ValueError("replay_receipt_hash must be 64-char hex sha256 when provided")
        if operation in FORBIDDEN_OPERATIONS:
            raise ValueError(f"forbidden_patch_operation: {operation}")
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"unsupported_patch_operation: {operation}")
        if is_dry_run is not True:
            raise ValueError("patch_runtime_v1_requires_dry_run")

        target = PatchRequest._validate_target_path(target_path)

        raw = "|".join([
            patch_id, target, patch_content_hash, rollback_bundle_hash,
            str(is_dry_run), operation, replay_receipt_hash,
            "|".join(sorted(allowlist_ids or [])), test_results_hash,
        ])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        request_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return PatchRequest(
            request_id=request_id,
            patch_id=patch_id,
            target_path=target,
            patch_content_hash=patch_content_hash,
            rollback_bundle_hash=rollback_bundle_hash,
            allowlist_ids=sorted(allowlist_ids or []),
            test_results_hash=test_results_hash,
            is_dry_run=True,
            is_valid=True,
            canonical_hash=canonical,
            operation=operation,
            replay_receipt_hash=replay_receipt_hash,
        )

    @staticmethod
    def _validate_target_path(path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("target_path required")
        path = path.strip()
        if path.startswith("/"):
            raise ValueError("absolute_path_rejected")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in path:
                raise ValueError(f"path_traversal_rejected: {pattern}")
        for root in FORBIDDEN_ROOTS:
            stripped = root.lower().lstrip("/")
            if stripped and path.lower().lstrip("/").startswith(stripped):
                raise ValueError(f"forbidden_root: {root}")
        path_lower = path.lower()
        for pattern in MAIN_MUTATION_PATTERNS:
            if pattern.lower() in path_lower:
                raise ValueError(f"main_mutation_rejected: {pattern}")
        if any(p in path_lower for p in ("git push", "git merge", "git branch -d", "git branch -D")):
            raise ValueError("git_destructive_operation_rejected")
        if any(p in path_lower for p in ("http://", "https://", "ssh://", "ftp://", "scp://")):
            raise ValueError("network_path_rejected")
        if any(c in path for c in ("|", ";", "&", "$", "`", "(", ")", "{", "}", "<", ">")):
            raise ValueError("freeform_shell_rejected")
        return path

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
