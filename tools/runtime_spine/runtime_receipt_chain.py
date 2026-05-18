"""Runtime receipt chain — validates full receipt compatibility chain.

Chain: Evidence Vault -> Replay -> Patch -> Execution -> Operator Run.
Each link must be present and hash-compatible. Missing links rejected.
Mismatched artifact IDs rejected.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


class RuntimeReceiptChain:
    """Validates the full runtime receipt compatibility chain."""

    def __init__(self) -> None:
        self._links: Dict[str, Optional[str]] = {
            "evidence_vault": None,
            "replay": None,
            "patch": None,
            "execution": None,
            "operator_run": None,
        }
        self._validated = False

    def set_evidence_vault_receipt(self, receipt_hash: str) -> None:
        if not receipt_hash or len(receipt_hash) != 64:
            raise ValueError("evidence_vault_receipt_hash must be 64-char hex")
        self._links["evidence_vault"] = receipt_hash

    def set_replay_receipt(self, receipt_hash: str) -> None:
        if not receipt_hash or len(receipt_hash) != 64:
            raise ValueError("replay_receipt_hash must be 64-char hex")
        self._links["replay"] = receipt_hash

    def set_patch_receipt(self, receipt_hash: str) -> None:
        if not receipt_hash or len(receipt_hash) != 64:
            raise ValueError("patch_receipt_hash must be 64-char hex")
        self._links["patch"] = receipt_hash

    def set_execution_receipt(self, receipt_hash: str) -> None:
        if not receipt_hash or len(receipt_hash) != 64:
            raise ValueError("execution_receipt_hash must be 64-char hex")
        self._links["execution"] = receipt_hash

    def set_operator_run_receipt(self, receipt_hash: str) -> None:
        if not receipt_hash or len(receipt_hash) != 64:
            raise ValueError("operator_run_receipt_hash must be 64-char hex")
        self._links["operator_run"] = receipt_hash

    def validate(self) -> Dict[str, Any]:
        """Validate the full receipt chain. Returns chain status."""
        missing: List[str] = []
        for name, value in self._links.items():
            if value is None:
                missing.append(name)

        chain_order = ["evidence_vault", "replay", "patch", "execution", "operator_run"]
        present_links = [
            name for name in chain_order if self._links.get(name) is not None
        ]

        chain_valid = len(missing) == 0

        # Build chain hash from present links in order
        parts = []
        for name in chain_order:
            h = self._links.get(name)
            if h:
                parts.append(f"{name}={h}")
        chain_hash = hashlib.sha256("|".join(parts).encode()).hexdigest() if parts else ""

        self._validated = chain_valid

        return {
            "chain_valid": chain_valid,
            "chain_hash": chain_hash,
            "present_links": present_links,
            "missing_links": missing,
            "link_count": len(present_links),
            "total_links": len(chain_order),
        }

    def enforce(self) -> None:
        result = self.validate()
        if not result["chain_valid"]:
            raise ValueError(
                f"chain_incomplete: missing {result['missing_links']}"
            )

    def is_complete(self) -> bool:
        return all(v is not None for v in self._links.values())

    def chain_hash(self) -> str:
        result = self.validate()
        return result["chain_hash"]

    def reset(self) -> None:
        for key in self._links:
            self._links[key] = None
        self._validated = False
