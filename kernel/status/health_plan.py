"""Ordered V12 health-plan targets."""

from __future__ import annotations

__all__ = ["ordered_health_plan"]

_PLAN = [
    "test-leak-prevention-foundation",
    "test-security-truth-substrate",
    "test-task-foundation",
    "test-cli-foundation",
    "test-dry-run-runtime-foundation",
    "test-replay-foundation",
    "test-audit-export-foundation",
    "test-local-status-foundation",
    "test-provider-mock-foundation",
    "test-notification-mock-foundation",
    "test-vault-contract-foundation",
    "test-daemon-contract-foundation",
    "test-domain-pipeline-contracts",
    "test-dashboard-contracts",
    "test-v12-foundation-progress-audit",
]


def ordered_health_plan() -> list[str]:
    return list(_PLAN)
