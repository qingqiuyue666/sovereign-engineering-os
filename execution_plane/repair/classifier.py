"""Classify failure bundles for local patch repair eligibility."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_plane.runtime.error_convergence import PATCH_REPAIRABLE_FAILURE_CODES


def classify_repairable_failure(bundle: Mapping[str, Any]) -> dict[str, Any]:
    failure_code = str(bundle.get("failure_code") or _failure_code_from_summary(bundle) or "EXECUTION_FAILED")
    trace_text = "\n".join(
        str(bundle.get(key) or "")
        for key in ("traceback", "stderr", "log_excerpt", "failure_summary", "schema_validation_stack")
    )
    target_files = _target_files(bundle)
    has_code_context = bool(target_files or bundle.get("adapter_module_path"))
    has_failure_stack = "Traceback" in trace_text or bool(bundle.get("schema_validation_stack"))
    repairable = failure_code in PATCH_REPAIRABLE_FAILURE_CODES and (has_code_context or has_failure_stack)
    reason = "repairable_code_level_failure" if repairable else "not_code_level_or_missing_context"
    return {
        "schema_version": "seos.patch_repair_classification.v1",
        "failure_code": failure_code,
        "repairable": repairable,
        "reason": reason,
        "has_traceback": "Traceback" in trace_text,
        "has_schema_stack": bool(bundle.get("schema_validation_stack")),
        "target_files": target_files,
        "adapter_module_path": bundle.get("adapter_module_path"),
    }


def _failure_code_from_summary(bundle: Mapping[str, Any]) -> str | None:
    summary = str(bundle.get("failure_summary") or "")
    if ":" not in summary:
        return None
    prefix = summary.split(":", 1)[0].strip()
    return prefix or None


def _target_files(bundle: Mapping[str, Any]) -> list[str]:
    raw = bundle.get("target_files")
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    module_path = bundle.get("adapter_module_path")
    return [str(module_path)] if module_path else []
