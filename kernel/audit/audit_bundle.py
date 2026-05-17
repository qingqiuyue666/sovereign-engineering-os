"""Audit bundle validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.security.security_classification import validate_classification

__all__ = ["AuditBundleResult", "validate_audit_bundle"]

_REQUIRED = ("bundle_id", "task_id", "run_id", "policy_version", "code_version", "receipt_refs", "event_digest_chain", "failure_bundle_refs", "replay_verdict_ref", "redaction_status")


@dataclass(frozen=True)
class AuditBundleResult:
    accepted: bool
    failures: tuple[str, ...]


def validate_audit_bundle(bundle: Mapping[str, object]) -> AuditBundleResult:
    if not isinstance(bundle, Mapping):
        return AuditBundleResult(False, ("audit_bundle_must_be_mapping",))
    failures: list[str] = []
    for field in _REQUIRED:
        if field not in bundle:
            failures.append(f"{field}_required")
    for field in ("bundle_id", "task_id", "run_id", "policy_version", "code_version", "replay_verdict_ref", "redaction_status"):
        if field in bundle and (not isinstance(bundle.get(field), str) or not bundle.get(field)):
            failures.append(f"{field}_must_be_nonempty_string")
    if "classification" in bundle and not validate_classification(bundle.get("classification")).accepted:
        failures.append("classification_unknown")
    for list_field in ("receipt_refs", "event_digest_chain", "failure_bundle_refs"):
        value = bundle.get(list_field)
        if not isinstance(value, list):
            failures.append(f"{list_field}_must_be_list")
    chain = bundle.get("event_digest_chain")
    if isinstance(chain, list) and not all(isinstance(item, str) and item.startswith("sha256:") for item in chain):
        failures.append("event_digest_chain_must_be_digest_list")
    return AuditBundleResult(not failures, tuple(sorted(set(failures))))
