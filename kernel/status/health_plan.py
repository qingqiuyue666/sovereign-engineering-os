"""Ordered V12 health-plan targets.

Includes all V12-05 through V12-08 boundary gates alongside
existing V11/V12 foundation gates.
"""

from __future__ import annotations

__all__ = ["ordered_health_plan"]

_PLAN = [
    "test-leak-prevention-foundation",
    "test-security-truth-substrate",
    "test-task-foundation",
    "test-cli-foundation",
    "test-dry-run-runtime-foundation",
    "test-runtime-runner-event-journal",
    "test-failurebundle-replay-foundation",
    "test-replay-foundation",
    "test-audit-export-foundation",
    "test-local-status-foundation",
    "test-provider-mock-foundation",
    "test-evidence-vault-boundary-foundation",
    "test-provider-execution-plane-boundary",
    "test-notification-mock-foundation",
    "test-vault-contract-foundation",
    "test-daemon-contract-foundation",
    "test-domain-pipeline-contracts",
    "test-dashboard-contracts",
    "test-v12-foundation-progress-audit",
]


def ordered_health_plan() -> list[str]:
    return list(_PLAN)
