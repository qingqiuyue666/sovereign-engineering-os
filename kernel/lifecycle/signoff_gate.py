"""
Sign-off gate skeleton: §31 baseline checks for the first narrow slice.

Constitutional anchors:
- v11 §31 Sign-Off Rule (current-stage signable path)
- v11 §22.10 (invariant binding)
- foundation §4.5 Section 31 extraction focus
- foundation §8 module mapping (P1 required before sign-off)

This module does NOT evaluate full constitutional breadth. It evaluates
the narrow-path baseline conditions named in §31:
- core contracts formalized and executable
- frozen schemas present for required slice artifacts
- replay honesty checks active
- capability/approval/side-effect governance active on the slice
- context completeness checks active
- retention/pinning explicitly declared
- invariant coverage non-zero

Phase-1 posture: each check is a simple *presence* probe over the code
and schema artifacts present in this repository. It does not pretend to
evaluate runtime correctness; that is the job of the tracer-bullet and
acceptance test matrix in `validation/tests/acceptance/*`. The gate's
value in phase 1 is to refuse sign-off if any required artifact is
missing (honest coverage).

The gate returns a structured `SignoffReport` listing pass/fail per
check; the caller is expected to surface it. `all_passed()` is the
single atomic truth signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from kernel.schemas import SCHEMA_FREEZE_TAG


#: First-slice schema artifacts that MUST be present under
#: `kernel/schemas/*.schema.json` for sign-off to proceed.
REQUIRED_SCHEMAS: tuple[str, ...] = (
    "context_artifact",
    "inference_artifact",
    "patch_proposal",
    "validation_receipt",
    "review_artifact",
    "approval_artifact",
    "replay_anchor",
    "capability_token",
    "audit_record",
    "failure_bundle",
    "taint_record",
    "drift_event_record",
    "revision",
    "journal_entry",
    "snapshot_root",
)

#: Contract modules that must exist (non-empty) to claim contract formalization.
REQUIRED_CONTRACT_MODULES: tuple[str, ...] = (
    "kernel/contracts/capability_rules.py",
)

#: Core services that must exist for capability/approval/context/replay
#: governance to be claimed "active".
REQUIRED_SERVICE_MODULES: tuple[str, ...] = (
    "kernel/services/capability_service.py",
    "kernel/services/context_service.py",
    "kernel/services/inference_service.py",
)

#: Other load-bearing modules required by Section 31.
REQUIRED_KERNEL_MODULES: tuple[str, ...] = (
    "kernel/lifecycle/stage_types.py",
    "kernel/lifecycle/signable_path_orchestrator.py",
    "kernel/version/version_tuple.py",
    "kernel/replay/replay_classifier.py",
    "kernel/evidence/append_only_ledger.py",
    "kernel/stores/sqlite/wal_recovery.py",
    "kernel/stores/sqlite/migrations/0001_core_signable_path.sql",
    "validation/quarantine/runner_adapter.py",
)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class SignoffReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append(CheckResult(name=name, passed=passed, detail=detail))

    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def failing(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def as_dict(self) -> Mapping[str, object]:
        return {
            "all_passed": self.all_passed(),
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
        }


class SignoffGate:
    """§31 narrow-path sign-off baseline gate.

    Instantiate with the repository root; call `evaluate()` to produce a
    `SignoffReport`. The gate does no I/O other than filesystem presence
    probes inside the repository root.
    """

    def __init__(self, repo_root: Path | str) -> None:
        self._root = Path(repo_root)

    # ------------------------------------------------------------------
    # individual checks
    # ------------------------------------------------------------------

    def _check_frozen_schemas(self, report: SignoffReport) -> None:
        missing: list[str] = []
        for name in REQUIRED_SCHEMAS:
            p = self._root / "kernel" / "schemas" / f"{name}.schema.json"
            if not p.is_file():
                missing.append(name)
        if missing:
            report.add(
                "frozen_schemas_present",
                False,
                f"missing schemas: {missing}",
            )
        else:
            report.add(
                "frozen_schemas_present",
                True,
                f"all {len(REQUIRED_SCHEMAS)} slice schemas present "
                f"(freeze tag: {SCHEMA_FREEZE_TAG})",
            )

    def _check_contract_modules(self, report: SignoffReport) -> None:
        missing = [
            m for m in REQUIRED_CONTRACT_MODULES if not (self._root / m).is_file()
        ]
        report.add(
            "core_contracts_formalized",
            not missing,
            f"missing contract modules: {missing}" if missing else "contract modules present",
        )

    def _check_service_modules(self, report: SignoffReport) -> None:
        missing = [
            m for m in REQUIRED_SERVICE_MODULES if not (self._root / m).is_file()
        ]
        report.add(
            "capability_approval_context_governance_active",
            not missing,
            f"missing service modules: {missing}" if missing else "services present",
        )

    def _check_kernel_modules(self, report: SignoffReport) -> None:
        missing = [
            m for m in REQUIRED_KERNEL_MODULES if not (self._root / m).is_file()
        ]
        report.add(
            "kernel_modules_present",
            not missing,
            f"missing kernel modules: {missing}" if missing else "kernel modules present",
        )

    def _check_replay_honesty(self, report: SignoffReport) -> None:
        # Replay honesty is claimed "active" iff the replay classifier
        # module exists AND the replay anchor schema is in the frozen
        # pack. This is a presence probe, not a runtime proof.
        classifier_ok = (
            self._root / "kernel" / "replay" / "replay_classifier.py"
        ).is_file()
        schema_ok = (
            self._root / "kernel" / "schemas" / "replay_anchor.schema.json"
        ).is_file()
        report.add(
            "replay_honesty_active",
            classifier_ok and schema_ok,
            (
                "replay classifier + replay_anchor schema present"
                if (classifier_ok and schema_ok)
                else f"classifier={classifier_ok}, schema={schema_ok}"
            ),
        )

    def _check_context_completeness(self, report: SignoffReport) -> None:
        ctx_service = (
            self._root / "kernel" / "services" / "context_service.py"
        ).is_file()
        ctx_schema = (
            self._root / "kernel" / "schemas" / "context_artifact.schema.json"
        ).is_file()
        report.add(
            "context_completeness_active",
            ctx_service and ctx_schema,
            "context service + context_artifact schema present"
            if (ctx_service and ctx_schema)
            else f"service={ctx_service}, schema={ctx_schema}",
        )

    def _check_retention_declaration(self, report: SignoffReport) -> None:
        # Phase-1 retention/pinning declaration is minimum-explicit:
        # we require the taint_record and failure_bundle schemas to be
        # present (they carry retention classes) AND the quarantine
        # runner_adapter to declare its posture. This is the honest
        # phase-1 "retention and pinning are explicit" surface.
        taint_ok = (
            self._root / "kernel" / "schemas" / "taint_record.schema.json"
        ).is_file()
        fb_ok = (
            self._root / "kernel" / "schemas" / "failure_bundle.schema.json"
        ).is_file()
        runner_ok = (
            self._root / "validation" / "quarantine" / "runner_adapter.py"
        ).is_file()
        report.add(
            "retention_and_pinning_declared",
            taint_ok and fb_ok and runner_ok,
            "taint_record + failure_bundle schemas + quarantine posture declared"
            if (taint_ok and fb_ok and runner_ok)
            else f"taint={taint_ok}, failure_bundle={fb_ok}, runner={runner_ok}",
        )

    def _check_invariant_coverage_nonzero(self, report: SignoffReport) -> None:
        # Phase-1 presence probe: the implementation foundation document
        # names the first-slice invariants, so the presence of that file
        # in-tree is our honest "non-zero coverage is declared" signal.
        foundation = (
            self._root
            / "governance"
            / "implementation"
            / "v11_narrow_path_implementation_foundation.md"
        ).is_file()
        constitution = (
            self._root
            / "governance"
            / "constitution"
            / "sovereign_engineering_operating_system_master_plan_v11.txt"
        ).is_file()
        report.add(
            "invariant_coverage_declared",
            foundation and constitution,
            "baseline foundation + constitution present"
            if (foundation and constitution)
            else f"foundation={foundation}, constitution={constitution}",
        )

    # ------------------------------------------------------------------
    # entry point
    # ------------------------------------------------------------------

    def evaluate(self) -> SignoffReport:
        report = SignoffReport()
        self._check_frozen_schemas(report)
        self._check_contract_modules(report)
        self._check_service_modules(report)
        self._check_kernel_modules(report)
        self._check_replay_honesty(report)
        self._check_context_completeness(report)
        self._check_retention_declaration(report)
        self._check_invariant_coverage_nonzero(report)
        return report
