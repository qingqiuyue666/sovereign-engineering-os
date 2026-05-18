"""Provider evidence binding placeholder — validates evidence binding presence.

In v1, evidence binding is required but the actual content is not yet
validated against the evidence vault. This placeholder ensures the binding
field is present and well-formed for future integration with Evidence Vault.

The binding is stored as a hash reference that the Runtime Receipt Spine
can link to in a future branch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class EvidenceBindingResult:
    """Immutable result of evidence binding validation."""
    valid: bool
    binding_present: bool
    binding_hash: str
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "binding_present": self.binding_present,
            "binding_hash": self.binding_hash,
            "failures": list(self.failures),
        }


def validate_evidence_binding(
    evidence_binding: str,
    require_present: bool = True,
) -> EvidenceBindingResult:
    """Validate an evidence binding reference.

    In v1, we verify the binding is present and well-formed. Future branches
    will validate the binding against the evidence vault.

    Args:
        evidence_binding: The evidence binding reference string.
        require_present: If True, rejection when missing. Default True.

    Returns:
        EvidenceBindingResult with validation details.
    """
    failures: list[str] = []

    present = isinstance(evidence_binding, str) and bool(evidence_binding.strip())

    if require_present and not present:
        failures.append("evidence_binding_required")
    elif present and evidence_binding.strip() == "":
        failures.append("evidence_binding_empty")

    binding_hash = ""
    if present:
        binding_hash = hashlib.sha256(
            f"evidence_binding:{evidence_binding}".encode()
        ).hexdigest()

    return EvidenceBindingResult(
        valid=len(failures) == 0,
        binding_present=present,
        binding_hash=binding_hash,
        failures=tuple(failures),
    )
