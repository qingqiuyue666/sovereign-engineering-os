"""Deterministic JSON export for audit bundles."""

from __future__ import annotations

from typing import Mapping
import json

from kernel.security.secret_scanner import CoreSecretScanner

from .audit_bundle import validate_audit_bundle

__all__ = ["export_audit_bundle_json"]


def export_audit_bundle_json(bundle: Mapping[str, object], *, scanner: CoreSecretScanner | None = None) -> str:
    validation = validate_audit_bundle(bundle)
    if not validation.accepted:
        raise ValueError("audit_bundle_invalid:" + ",".join(validation.failures))
    text = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    scan = (scanner or CoreSecretScanner()).scan_text(text, path="audit_bundle_export")
    if not scan.clean:
        raise ValueError("audit_bundle_sensitive_content_blocked")
    return text + "\n"
