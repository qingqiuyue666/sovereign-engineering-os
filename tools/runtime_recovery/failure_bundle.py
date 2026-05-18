"""Failure bundle — captures and bundles failure evidence for recovery planning.

Binds failure evidence from failing runtime modules. Rejects empty bundles.
No secret material. No raw payload in bundle output.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class FailureBundle:
    """Immutable failure bundle with evidence binding."""

    bundle_id: str
    failed_module: str
    failure_codes: List[str]
    evidence_ids: List[str]
    failure_hash: str
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        failed_module: str,
        failure_codes: List[str],
        evidence_ids: List[str],
    ) -> FailureBundle:
        if not failed_module.strip():
            raise ValueError("failed_module required")
        if not failure_codes:
            raise ValueError("failure_codes must not be empty")
        if not evidence_ids:
            raise ValueError("evidence_ids must not be empty")

        for eid in evidence_ids:
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError(f"invalid evidence_id: {eid}")

        raw = "|".join([
            failed_module,
            "|".join(sorted(failure_codes)),
            "|".join(sorted(evidence_ids)),
        ])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        bundle_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()
        failure_hash = hashlib.sha256(
            f"{failed_module}|{'|'.join(sorted(failure_codes))}".encode()
        ).hexdigest()

        return FailureBundle(
            bundle_id=bundle_id,
            failed_module=failed_module,
            failure_codes=sorted(failure_codes),
            evidence_ids=sorted(evidence_ids),
            failure_hash=failure_hash,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
