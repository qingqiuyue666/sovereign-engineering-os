"""Audit trail with SHA-256 hash chaining for tamper evidence."""

from __future__ import annotations

from kernel.audit.trail import AuditTrail, AuditEntry, audit, get_global_trail
from kernel.audit.hashchain import HashChain, HashChainEntry, verify_chain

__all__ = [
    "AuditTrail",
    "AuditEntry",
    "audit",
    "get_global_trail",
    "HashChain",
    "HashChainEntry",
    "verify_chain",
]
