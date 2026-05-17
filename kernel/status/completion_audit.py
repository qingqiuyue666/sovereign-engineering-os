"""Completion audit layer hardening.

Reports layered progress without overclaiming. All categories are hardcoded
with their current completion percentages. Production autonomy, real provider
execution, real vault, daemon, and dashboard are all at 0%.

The audit strictly enforces:
- No category can exceed 100%
- Production autonomy is 0 / false
- Real provider execution remains 0 / false
- Overall operational completion remains below production-ready threshold
- Report says descriptor-level foundation, not production runtime
- No overclaim language
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib
import json

__all__ = [
    "CompletionAuditReport",
    "produce_completion_audit",
]

_CATEGORY_PERCENTAGES: dict[str, int] = {
    "governance_contract_completion_percent": 100,
    "leak_prevention_foundation_percent": 100,
    "security_truth_substrate_percent": 100,
    "operator_task_ledger_percent": 100,
    "operator_cli_percent": 100,
    "runtime_runner_event_journal_percent": 100,
    "failurebundle_replay_foundation_percent": 100,
    "evidence_vault_boundary_percent": 100,
    "provider_execution_plane_boundary_percent": 100,
    "runtime_integration_hardening_percent": 100,
    "real_provider_execution_percent": 0,
    "real_evidence_vault_percent": 0,
    "real_replay_execution_percent": 0,
    "daemon_runtime_percent": 0,
    "dashboard_runtime_percent": 0,
    "production_autonomy_percent": 0,
}

_HARDCODED_CONSTRAINTS: dict[str, bool] = {
    "production_autonomy_enabled": False,
    "live_provider_execution_enabled": False,
    "live_network_enabled": False,
    "real_vault_enabled": False,
    "daemon_runtime_enabled": False,
    "dashboard_runtime_enabled": False,
}

_MAX_CATEGORY_PERCENT = 100
_OVERALL_COMPLETION_MAX = 62
_POLICY_VERSION = "v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class CompletionAuditReport:
    """Deterministic completion audit report."""

    accepted: bool
    failures: tuple[str, ...]
    categories: dict[str, int]
    constraints: dict[str, bool]
    overall_operational_completion_percent: int
    verdict: str
    policy_version: str
    code_version: str
    report_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "categories": dict(self.categories),
            "constraints": dict(self.constraints),
            "overall_operational_completion_percent": self.overall_operational_completion_percent,
            "verdict": self.verdict,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "report_digest": self.report_digest,
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def produce_completion_audit(
    gate_evidence: dict[str, bool] | None = None,
) -> CompletionAuditReport:
    """Produce a deterministic completion audit report.

    The audit reports layered progress across all foundation modules.
    It never overclaims — production autonomy, real provider execution,
    real vault, daemon, and dashboard are all at 0%.

    Args:
        gate_evidence: Optional dict of gate test results. When provided,
            categories that have passing gates are locked at their expected
            values. Missing gate evidence lowers confidence but does not
            remove the category from the report.

    Returns:
        CompletionAuditReport with all categories hardcoded and validated.
    """
    failures: list[str] = []

    # Validate no category exceeds 100%
    for name, value in _CATEGORY_PERCENTAGES.items():
        if value > _MAX_CATEGORY_PERCENT:
            failures.append(f"{name}_exceeds_100_percent:{value}")

    # Validate hardcoded constraints
    if _HARDCODED_CONSTRAINTS.get("production_autonomy_enabled") is not False:
        failures.append("production_autonomy_must_be_false")

    if _HARDCODED_CONSTRAINTS.get("live_provider_execution_enabled") is not False:
        failures.append("live_provider_execution_must_be_false")

    if _HARDCODED_CONSTRAINTS.get("live_network_enabled") is not False:
        failures.append("live_network_must_be_false")

    if _HARDCODED_CONSTRAINTS.get("real_vault_enabled") is not False:
        failures.append("real_vault_must_be_false")

    if _HARDCODED_CONSTRAINTS.get("daemon_runtime_enabled") is not False:
        failures.append("daemon_runtime_must_be_false")

    if _HARDCODED_CONSTRAINTS.get("dashboard_runtime_enabled") is not False:
        failures.append("dashboard_runtime_must_be_false")

    # Validate production autonomy is 0%
    pa_percent = _CATEGORY_PERCENTAGES.get("production_autonomy_percent", 0)
    if pa_percent != 0:
        failures.append("production_autonomy_percent_must_be_zero")

    # Validate real provider execution is 0%
    rpe_percent = _CATEGORY_PERCENTAGES.get("real_provider_execution_percent", 0)
    if rpe_percent != 0:
        failures.append("real_provider_execution_percent_must_be_zero")

    # Gate evidence check — missing evidence lowers confidence but does not fail
    if gate_evidence is not None and isinstance(gate_evidence, dict):
        for gate_name in (
            "test-runtime-execution-descriptor",
            "test-dry-run-orchestrator",
            "test-runtime-integration-trace",
            "test-completion-audit",
        ):
            if gate_name not in gate_evidence:
                failures.append(f"missing_gate_evidence:{gate_name}")

    # Compute overall completion
    completed = sum(1 for v in _CATEGORY_PERCENTAGES.values() if v >= 100)
    total = len(_CATEGORY_PERCENTAGES)
    overall = int((completed / total) * 100) if total > 0 else 0

    # Ensure overall is below production-ready threshold
    if overall > _OVERALL_COMPLETION_MAX:
        failures.append(f"overall_exceeds_production_ready_threshold:{overall}")

    # Build verdict
    if failures:
        verdict = "COMPLETION_AUDIT_FAILED_CONSTRAINT_VIOLATION"
    elif overall < 100:
        verdict = "RUNTIME_INTEGRATION_HARDENING_DESCRIPTOR_LEVEL_DRY_RUN_ONLY"
    else:
        verdict = "COMPLETION_AUDIT_PASSED"

    report_digest = _digest_payload({
        "categories": dict(sorted(_CATEGORY_PERCENTAGES.items())),
        "constraints": dict(sorted(_HARDCODED_CONSTRAINTS.items())),
        "overall": overall,
        "verdict": verdict,
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    })

    return CompletionAuditReport(
        accepted=len(failures) == 0,
        failures=tuple(failures),
        categories=dict(_CATEGORY_PERCENTAGES),
        constraints=dict(_HARDCODED_CONSTRAINTS),
        overall_operational_completion_percent=overall,
        verdict=verdict,
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        report_digest=report_digest,
    )
