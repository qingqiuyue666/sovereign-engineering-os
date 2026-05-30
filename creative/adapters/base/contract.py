"""Base class and contract builder for safe creative adapters."""

from __future__ import annotations

from dataclasses import dataclass
from creative.common import ADAPTER_LEVELS, SCHEMA_VERSION
from creative.adapters.base.result import AdapterResult

@dataclass(frozen=True)
class AdapterContract:
    name: str
    level: str
    supports_execute: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "level": self.level,
            "supports_execute": self.supports_execute,
            "required_methods": [
                "detect",
                "validate_environment",
                "plan",
                "dry_run",
                "execute",
                "collect_evidence",
                "build_report",
            ],
            "allowed_levels": list(ADAPTER_LEVELS),
        }

    def detect(self) -> AdapterResult:
        return AdapterResult(self.name, "detect", "FOUND_BUT_UNTESTED")

    def validate_environment(self) -> AdapterResult:
        return AdapterResult(self.name, "validate_environment", "FOUND_BUT_UNTESTED")

    def plan(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(self.name, "plan", "PLANNED", metadata={"job": job})

    def dry_run(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(self.name, "dry_run", "DRY_RUN_READY", metadata={"job": job})

    def execute(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(self.name, "execute", "USER_APPROVAL_REQUIRED", failures=("USER_APPROVAL_REQUIRED",), metadata={"job": job})

    def collect_evidence(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(self.name, "collect_evidence", "EVIDENCE_PLANNED", metadata={"job": job})

    def build_report(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(self.name, "build_report", "REPORT_PLANNED", metadata={"job": job})

def build_adapter_contract(name: str, level: str = "LEVEL_1_DRY_RUN") -> AdapterContract:
    return AdapterContract(name=name, level=level, supports_execute=False)
