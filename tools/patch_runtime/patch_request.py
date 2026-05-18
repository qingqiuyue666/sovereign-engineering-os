"""Patch request — immutable patch request contract.

Validates patch request structure, target paths, and safety constraints.
Rejects absolute paths, path traversal, forbidden roots, and main mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List


FORBIDDEN_ROOTS = frozenset({"/", "/etc", "/proc", "/sys", "/dev", "/boot", "/root"})
FORBIDDEN_PATTERNS = ("..", "~", "$HOME", "${HOME}", "%HOME%")
MAIN_MUTATION_PATTERNS = ("git checkout main", "git switch main", "git push", "git merge", "git branch -d", "git branch -D")


@dataclass(frozen=True)
class PatchRequest:
    """Immutable patch request with validated target and safety checks."""

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
    ) -> PatchRequest:
        if not patch_id.strip():
            raise ValueError("patch_id required")
        if not patch_content_hash or len(patch_content_hash) != 64:
            raise ValueError("patch_content_hash must be 64-char hex sha256")
        if not rollback_bundle_hash or len(rollback_bundle_hash) != 64:
            raise ValueError("rollback_bundle_hash must be 64-char hex sha256")

        # Path safety validation
        target = PatchRequest._validate_target_path(target_path)

        raw = "|".join([
            patch_id, target, patch_content_hash, rollback_bundle_hash,
            str(is_dry_run), "|".join(sorted(allowlist_ids or [])), test_results_hash,
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
            is_dry_run=is_dry_run,
            is_valid=True,
            canonical_hash=canonical,
        )

    @staticmethod
    def _validate_target_path(path: str) -> str:
        if not path or not path.strip():
            raise ValueError("target_path required")
        path = path.strip()

        # Reject absolute paths
        if path.startswith("/"):
            raise ValueError("absolute_path_rejected")

        # Reject path traversal
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in path:
                raise ValueError(f"path_traversal_rejected: {pattern}")

        # Reject forbidden roots
        for root in FORBIDDEN_ROOTS:
            stripped = root.lower().lstrip("/")
            if stripped and path.lower().lstrip("/").startswith(stripped):
                raise ValueError(f"forbidden_root: {root}")

        # Reject main mutation patterns
        path_lower = path.lower()
        for pattern in MAIN_MUTATION_PATTERNS:
            if pattern.lower() in path_lower:
                raise ValueError(f"main_mutation_rejected: {pattern}")

        # Reject git push/merge/branch delete
        if any(p in path_lower for p in ("git push", "git merge", "git branch -d", "git branch -D")):
            raise ValueError("git_destructive_operation_rejected")

        # Reject network patterns in path
        if any(p in path_lower for p in ("http://", "https://", "ssh://", "ftp://", "scp://")):
            raise ValueError("network_path_rejected")

        # Reject freeform shell
        if any(c in path for c in ("|", ";", "&", "$", "`", "(", ")", "{", "}", "<", ">")):
            raise ValueError("freeform_shell_rejected")

        return path

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
