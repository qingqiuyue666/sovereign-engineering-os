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

Phase-1 posture: most checks are simple *presence* probes over the code
and schema artifacts present in this repository. The
`invariant_coverage_declared` check is the first minimally proof-linked
check: it reads `governance/implementation/invariant_bindings.yaml` and
requires each declared invariant to name enforcement and test-carrier
evidence. Runtime correctness remains the job of the tracer-bullet and
acceptance test matrix in `validation/tests/acceptance/*`.

The gate returns a structured `SignoffReport` listing pass/fail per
check; the caller is expected to surface it. `all_passed()` is the
single atomic truth signal.
"""

from __future__ import annotations

import ast
import json
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

INVARIANT_BINDINGS_PATH = "governance/implementation/invariant_bindings.yaml"

TEST_CARRIER_ROOTS: tuple[str, ...] = (
    "validation/tests/acceptance",
    "tests/tracer_bullet",
    "tests/schemas",
)


@dataclass(frozen=True)
class InvariantBinding:
    invariant_id: str
    enforcement_module: str
    acceptance_test_ids: tuple[str, ...]


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
    `SignoffReport`. The gate does only local filesystem reads inside the
    repository root.
    """

    def __init__(self, repo_root: Path | str) -> None:
        self._root = Path(repo_root)

    # ------------------------------------------------------------------
    # individual checks
    # ------------------------------------------------------------------

    def _check_frozen_schemas(self, report: SignoffReport) -> None:
        missing: list[str] = []
        invalid_json: list[str] = []
        invalid_version: list[str] = []
        for name in REQUIRED_SCHEMAS:
            p = self._root / "kernel" / "schemas" / f"{name}.schema.json"
            if not p.is_file():
                missing.append(name)
                continue
            try:
                schema = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                invalid_json.append(name)
                continue
            if (
                not isinstance(schema, dict)
                or schema.get("schema_version") != SCHEMA_FREEZE_TAG
            ):
                invalid_version.append(name)
        failures: list[str] = []
        if missing:
            failures.append(f"missing schemas: {missing}")
        if invalid_json:
            failures.append(f"unparseable schema json: {invalid_json}")
        if invalid_version:
            failures.append(
                f"schema_version mismatch: {invalid_version} "
                f"(expected {SCHEMA_FREEZE_TAG})"
            )
        if failures:
            report.add(
                "frozen_schemas_present",
                False,
                "; ".join(failures),
            )
        else:
            report.add(
                "frozen_schemas_present",
                True,
                f"all {len(REQUIRED_SCHEMAS)} slice schemas parse with "
                f"schema_version={SCHEMA_FREEZE_TAG} "
                f"(freeze tag: {SCHEMA_FREEZE_TAG})",
            )

    def _check_contract_modules(self, report: SignoffReport) -> None:
        missing: list[str] = []
        empty: list[str] = []
        syntax_invalid: list[str] = []
        for module in REQUIRED_CONTRACT_MODULES:
            path = self._root / module
            if not path.is_file():
                missing.append(module)
                continue
            source = path.read_text(encoding="utf-8")
            if not source.strip():
                empty.append(module)
                continue
            try:
                ast.parse(source, filename=module)
            except SyntaxError:
                syntax_invalid.append(module)
        failures: list[str] = []
        if missing:
            failures.append(f"missing contract modules: {missing}")
        if empty:
            failures.append(f"empty contract modules: {empty}")
        if syntax_invalid:
            failures.append(f"syntax-invalid contract modules: {syntax_invalid}")
        report.add(
            "core_contracts_formalized",
            not failures,
            "; ".join(failures)
            if failures
            else "contract modules present, non-empty, and syntax-valid",
        )

    def _check_service_modules(self, report: SignoffReport) -> None:
        missing: list[str] = []
        empty: list[str] = []
        syntax_invalid: list[str] = []
        for module in REQUIRED_SERVICE_MODULES:
            path = self._root / module
            if not path.is_file():
                missing.append(module)
                continue
            source = path.read_text(encoding="utf-8")
            if not source.strip():
                empty.append(module)
                continue
            if path.suffix == ".py":
                try:
                    ast.parse(source, filename=module)
                except SyntaxError:
                    syntax_invalid.append(module)
        failures: list[str] = []
        if missing:
            failures.append(f"missing service modules: {missing}")
        if empty:
            failures.append(f"empty service modules: {empty}")
        if syntax_invalid:
            failures.append(f"syntax-invalid service modules: {syntax_invalid}")
        report.add(
            "capability_approval_context_governance_active",
            not failures,
            "; ".join(failures)
            if failures
            else "service modules present, non-empty, and syntax-valid",
        )

    def _check_kernel_modules(self, report: SignoffReport) -> None:
        missing: list[str] = []
        empty: list[str] = []
        syntax_invalid: list[str] = []
        for module in REQUIRED_KERNEL_MODULES:
            path = self._root / module
            if not path.is_file():
                missing.append(module)
                continue
            source = path.read_text(encoding="utf-8")
            if not source.strip():
                empty.append(module)
                continue
            if path.suffix == ".py":
                try:
                    ast.parse(source, filename=module)
                except SyntaxError:
                    syntax_invalid.append(module)
        failures: list[str] = []
        if missing:
            failures.append(f"missing kernel modules: {missing}")
        if empty:
            failures.append(f"empty kernel modules: {empty}")
        if syntax_invalid:
            failures.append(f"syntax-invalid kernel modules: {syntax_invalid}")
        report.add(
            "kernel_modules_present",
            not failures,
            "; ".join(failures)
            if failures
            else "kernel modules/files present, non-empty, and Python entries syntax-valid",
        )

    def _check_replay_honesty(self, report: SignoffReport) -> None:
        # Minimal static replay-surface proof. This intentionally does
        # not import the classifier or prove replay semantics.
        classifier_module = "kernel/replay/replay_classifier.py"
        schema_name = "replay_anchor"
        classifier_path = self._root / classifier_module
        schema_path = self._root / "kernel" / "schemas" / f"{schema_name}.schema.json"

        failures: list[str] = []
        if not classifier_path.is_file():
            failures.append(f"missing replay classifier: {classifier_module}")
        else:
            source = classifier_path.read_text(encoding="utf-8")
            if not source.strip():
                failures.append(f"empty replay classifier: {classifier_module}")
            else:
                try:
                    ast.parse(source, filename=classifier_module)
                except SyntaxError:
                    failures.append(
                        f"syntax-invalid replay classifier: {classifier_module}"
                    )

        if not schema_path.is_file():
            failures.append(f"missing replay schema: {schema_name}")
        else:
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures.append(f"unparseable replay schema json: {schema_name}")
            else:
                if not isinstance(schema, dict):
                    failures.append(f"replay schema is not a JSON object: {schema_name}")
                elif schema.get("schema_version") != SCHEMA_FREEZE_TAG:
                    failures.append(
                        f"replay schema_version mismatch: {schema_name} "
                        f"(expected {SCHEMA_FREEZE_TAG})"
                    )

        report.add(
            "replay_honesty_active",
            not failures,
            "; ".join(failures)
            if failures
            else "replay classifier syntax-valid and replay_anchor schema frozen",
        )

    def _check_context_completeness(self, report: SignoffReport) -> None:
        service_module = "kernel/services/context_service.py"
        schema_name = "context_artifact"
        service_path = self._root / service_module
        schema_path = self._root / "kernel" / "schemas" / f"{schema_name}.schema.json"

        failures: list[str] = []
        if not service_path.is_file():
            failures.append(f"missing context service: {service_module}")
        else:
            source = service_path.read_text(encoding="utf-8")
            if not source.strip():
                failures.append(f"empty context service: {service_module}")
            else:
                try:
                    ast.parse(source, filename=service_module)
                except SyntaxError:
                    failures.append(f"syntax-invalid context service: {service_module}")

        if not schema_path.is_file():
            failures.append(f"missing context schema: {schema_name}")
        else:
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures.append(f"unparseable context schema json: {schema_name}")
            else:
                if not isinstance(schema, dict):
                    failures.append(f"context schema is not a JSON object: {schema_name}")
                elif schema.get("schema_version") != SCHEMA_FREEZE_TAG:
                    failures.append(
                        f"context schema_version mismatch: {schema_name} "
                        f"(expected {SCHEMA_FREEZE_TAG})"
                    )

        report.add(
            "context_completeness_active",
            not failures,
            "; ".join(failures)
            if failures
            else "context service syntax-valid and context_artifact schema frozen",
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

    @staticmethod
    def _yaml_scalar(value: str) -> str:
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            return value[1:-1]
        return value

    def _read_invariant_bindings(
        self, path: Path
    ) -> tuple[InvariantBinding, ...]:
        bindings: list[InvariantBinding] = []
        current: dict[str, object] | None = None
        active_list: str | None = None

        def flush_current() -> None:
            if current is None:
                return
            raw_ids = current.get("acceptance_test_ids", ())
            ids = raw_ids if isinstance(raw_ids, list) else []
            bindings.append(
                InvariantBinding(
                    invariant_id=str(current.get("invariant_id", "")),
                    enforcement_module=str(current.get("enforcement_module", "")),
                    acceptance_test_ids=tuple(str(v) for v in ids),
                )
            )

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line == "---" or line.startswith("#"):
                continue

            if line.startswith("- invariant_id:"):
                flush_current()
                current = {
                    "invariant_id": self._yaml_scalar(line.split(":", 1)[1]),
                    "enforcement_module": "",
                    "acceptance_test_ids": [],
                }
                active_list = None
                continue

            if current is None:
                continue

            if line.startswith("enforcement_module:"):
                current["enforcement_module"] = self._yaml_scalar(
                    line.split(":", 1)[1]
                )
                active_list = None
                continue

            if line.startswith("acceptance_test_ids:"):
                active_list = "acceptance_test_ids"
                continue

            if active_list == "acceptance_test_ids" and line.startswith("- "):
                raw_ids = current.setdefault("acceptance_test_ids", [])
                if isinstance(raw_ids, list):
                    raw_ids.append(self._yaml_scalar(line[2:]))
                continue

            active_list = None

        flush_current()
        return tuple(bindings)

    def _test_carriers_for(self, test_id: str) -> tuple[Path, ...]:
        if test_id.startswith("AT-"):
            pattern = f"test_{test_id.lower().replace('-', '_')}*.py"
        else:
            pattern = f"{test_id}.py"

        carriers: list[Path] = []
        for rel_root in TEST_CARRIER_ROOTS:
            root = self._root / rel_root
            if root.is_dir():
                carriers.extend(p for p in root.rglob(pattern) if p.is_file())
        return tuple(carriers)

    def _check_invariant_coverage_nonzero(self, report: SignoffReport) -> None:
        # First minimally proof-linked signoff check. Keep scope narrow:
        # prove that declared invariant bindings name enforcement modules
        # and existing test carrier files. Do not inspect or clean up the
        # invariants themselves here.
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
        registry = self._root / INVARIANT_BINDINGS_PATH

        errors: list[str] = []
        if not foundation:
            errors.append("missing baseline foundation")
        if not constitution:
            errors.append("missing baseline constitution")
        if not registry.is_file():
            errors.append(f"missing invariant bindings: {INVARIANT_BINDINGS_PATH}")

        bindings: tuple[InvariantBinding, ...] = ()
        if registry.is_file():
            bindings = self._read_invariant_bindings(registry)
            if not bindings:
                errors.append("invariant bindings are empty")

        for binding in bindings:
            label = binding.invariant_id or "<missing invariant_id>"
            if not binding.enforcement_module:
                errors.append(f"{label} missing enforcement_module")
            if not binding.acceptance_test_ids:
                errors.append(f"{label} missing acceptance_test_ids")
            for test_id in binding.acceptance_test_ids:
                if not self._test_carriers_for(test_id):
                    errors.append(f"{label} test carrier missing for {test_id}")

        carrier_ref_count = sum(len(b.acceptance_test_ids) for b in bindings)
        report.add(
            "invariant_coverage_declared",
            not errors,
            (
                f"{len(bindings)} invariant bindings proof-linked to "
                f"{carrier_ref_count} test carrier refs"
                if not errors
                else "invariant proof links incomplete: "
                + "; ".join(errors[:5])
                + (f"; +{len(errors) - 5} more" if len(errors) > 5 else "")
            ),
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
