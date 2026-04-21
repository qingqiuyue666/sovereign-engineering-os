"""
Tracer-bullet test: sign-off gate correctness.

Foundation §4.5 + §6 step 10 definition of done:
  "sign-off gate reports pass/fail against slice obligations only"

Constitutional anchors:
- v11 §31 Sign-Off Rule (current-stage signable path)
- v11 §22.10 Invariant Enforcement Binding
- foundation §4.5 Section 31 extraction focus
- foundation §8 module mapping (P1 required before sign-off)
- foundation §17 INV-CAP-UI-STATE-IS-NOT-AUTHORITY (signoff gate proof)

This test verifies that the §31 sign-off gate:
1. Passes when the repository's required narrow-path artifacts are all
   present (in-tree baseline).
2. Fails fail-closed when a required schema, contract module, service
   module, or kernel module is absent (simulated via a throwaway
   repo-root directory tree).
3. Emits structured, actionable CheckResult entries (name, passed,
   detail) for each §31 baseline check.
4. Reports pass/fail atomically via `all_passed()`.
5. Does NOT pretend to evaluate constitutional breadth beyond §31 slice
   scope (the gate is a presence/proof-link probe, not a runtime proof).

The gate's scope is narrow-path only; any broader evaluation is out of
phase-1 scope and explicitly deferred by the foundation document.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repo root is on the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from kernel.lifecycle.signoff_gate import (
    CheckResult,
    REQUIRED_CONTRACT_MODULES,
    REQUIRED_KERNEL_MODULES,
    REQUIRED_SCHEMAS,
    REQUIRED_SERVICE_MODULES,
    SignoffGate,
    SignoffReport,
)
from kernel.schemas import SCHEMA_FREEZE_TAG


# Path to the actual repository root (two levels up from this file).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Test: in-tree repository passes the gate
# ---------------------------------------------------------------------------


class TestSignoffGatePassesOnLiveRepo(unittest.TestCase):
    """The §31 gate must PASS against the live baseline repository."""

    def test_all_checks_pass(self) -> None:
        """Each §31 slice check must be present and passing in-tree."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        self.assertTrue(
            report.all_passed(),
            f"signoff gate failed in live tree; failing checks: "
            f"{[c.name + ': ' + c.detail for c in report.failing()]}",
        )

    def test_report_has_nonzero_checks(self) -> None:
        """The report must emit at least one check (non-zero coverage)."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        self.assertGreater(len(report.checks), 0)

    def test_report_check_result_shape(self) -> None:
        """Every CheckResult must have name, passed:bool, detail:str."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        for check in report.checks:
            self.assertIsInstance(check, CheckResult)
            self.assertIsInstance(check.name, str)
            self.assertIsInstance(check.passed, bool)
            self.assertIsInstance(check.detail, str)
            self.assertTrue(len(check.name) > 0)
            self.assertTrue(len(check.detail) > 0)

    def test_report_as_dict_is_serializable(self) -> None:
        """`as_dict()` output must be JSON-serializable (audit portable)."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        blob = json.dumps(report.as_dict())
        self.assertIn("all_passed", blob)
        self.assertIn("checks", blob)

    def test_schema_freeze_tag_surfaced(self) -> None:
        """The frozen_schemas_present check must surface the freeze tag
        in its detail (foundation §3.3 freeze discipline)."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        schema_check = next(
            (c for c in report.checks if c.name == "frozen_schemas_present"),
            None,
        )
        self.assertIsNotNone(schema_check)
        self.assertTrue(schema_check.passed)
        self.assertIn(SCHEMA_FREEZE_TAG, schema_check.detail)


# ---------------------------------------------------------------------------
# Test: gate fails fail-closed on missing artifacts
# ---------------------------------------------------------------------------


class TestSignoffGateFailsOnMissingArtifacts(unittest.TestCase):
    """The §31 gate must FAIL fail-closed when required artifacts are
    absent. These tests use a throwaway empty directory as the repo
    root so no production artifacts are disturbed."""

    def test_empty_repo_fails_all_checks(self) -> None:
        """An empty directory must fail every presence check."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = SignoffGate(repo_root=Path(tmp))
            report = gate.evaluate()
            self.assertFalse(report.all_passed())
            # At least the schema, contract, service, kernel, and invariant
            # coverage checks must fail.
            failing_names = {c.name for c in report.failing()}
            self.assertIn("frozen_schemas_present", failing_names)
            self.assertIn("core_contracts_formalized", failing_names)
            self.assertIn(
                "capability_approval_context_governance_active", failing_names
            )
            self.assertIn("kernel_modules_present", failing_names)
            self.assertIn("invariant_coverage_declared", failing_names)

    def test_missing_schema_surfaces_explicit_detail(self) -> None:
        """When schemas are missing, the failing check must list names."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = SignoffGate(repo_root=Path(tmp))
            report = gate.evaluate()
            schema_check = next(
                (c for c in report.checks if c.name == "frozen_schemas_present"),
                None,
            )
            self.assertIsNotNone(schema_check)
            self.assertFalse(schema_check.passed)
            self.assertIn("missing schemas", schema_check.detail)

    def test_partial_missing_schema_rejects(self) -> None:
        """Removing a single required schema must cause gate to fail.

        This proves the gate does not admit partial coverage — every
        required §23 slice schema must be present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create every required schema...
            schema_dir = root / "kernel" / "schemas"
            schema_dir.mkdir(parents=True)
            for name in REQUIRED_SCHEMAS:
                (schema_dir / f"{name}.schema.json").write_text(
                    json.dumps(
                        {
                            "type": "object",
                            "schema_version": SCHEMA_FREEZE_TAG,
                        }
                    )
                )
            # ...except one (deliberately omitted).
            omitted = REQUIRED_SCHEMAS[0]
            (schema_dir / f"{omitted}.schema.json").unlink()

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            schema_check = next(
                c for c in report.checks if c.name == "frozen_schemas_present"
            )
            self.assertFalse(schema_check.passed)
            self.assertIn(omitted, schema_check.detail)

    def test_unparseable_schema_rejects(self) -> None:
        """A present but non-JSON schema must not satisfy the frozen pack."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir = root / "kernel" / "schemas"
            schema_dir.mkdir(parents=True)
            for name in REQUIRED_SCHEMAS:
                (schema_dir / f"{name}.schema.json").write_text(
                    json.dumps(
                        {
                            "type": "object",
                            "schema_version": SCHEMA_FREEZE_TAG,
                        }
                    )
                )
            broken = REQUIRED_SCHEMAS[0]
            (schema_dir / f"{broken}.schema.json").write_text("{not json")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            schema_check = next(
                c for c in report.checks if c.name == "frozen_schemas_present"
            )
            self.assertFalse(schema_check.passed)
            self.assertIn("unparseable schema json", schema_check.detail)
            self.assertIn(broken, schema_check.detail)

    def test_schema_version_mismatch_rejects(self) -> None:
        """Every required schema must declare the frozen schema version."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir = root / "kernel" / "schemas"
            schema_dir.mkdir(parents=True)
            for name in REQUIRED_SCHEMAS:
                (schema_dir / f"{name}.schema.json").write_text(
                    json.dumps(
                        {
                            "type": "object",
                            "schema_version": SCHEMA_FREEZE_TAG,
                        }
                    )
                )
            mismatched = REQUIRED_SCHEMAS[0]
            (schema_dir / f"{mismatched}.schema.json").write_text(
                json.dumps(
                    {
                        "type": "object",
                        "schema_version": "wrong-freeze",
                    }
                )
            )

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            schema_check = next(
                c for c in report.checks if c.name == "frozen_schemas_present"
            )
            self.assertFalse(schema_check.passed)
            self.assertIn("schema_version mismatch", schema_check.detail)
            self.assertIn(mismatched, schema_check.detail)
            self.assertIn(SCHEMA_FREEZE_TAG, schema_check.detail)

    def test_missing_contract_module_surfaces_path(self) -> None:
        """A missing contract module must produce a check failure whose
        detail names the missing path."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = SignoffGate(repo_root=Path(tmp))
            report = gate.evaluate()
            contract_check = next(
                (c for c in report.checks if c.name == "core_contracts_formalized"),
                None,
            )
            self.assertIsNotNone(contract_check)
            self.assertFalse(contract_check.passed)
            # Detail must list the missing module paths.
            for mod in REQUIRED_CONTRACT_MODULES:
                self.assertIn(mod, contract_check.detail)

    def test_empty_contract_module_rejects(self) -> None:
        """A present but empty contract module must not prove formalization."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mod in REQUIRED_CONTRACT_MODULES:
                p = root / mod
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            contract_check = next(
                c for c in report.checks if c.name == "core_contracts_formalized"
            )
            self.assertFalse(contract_check.passed)
            self.assertIn("empty contract modules", contract_check.detail)
            for mod in REQUIRED_CONTRACT_MODULES:
                self.assertIn(mod, contract_check.detail)

    def test_syntax_invalid_contract_module_rejects(self) -> None:
        """Contract module proof is import-free but requires valid Python."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mod in REQUIRED_CONTRACT_MODULES:
                p = root / mod
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("def not valid python\n")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            contract_check = next(
                c for c in report.checks if c.name == "core_contracts_formalized"
            )
            self.assertFalse(contract_check.passed)
            self.assertIn("syntax-invalid contract modules", contract_check.detail)
            for mod in REQUIRED_CONTRACT_MODULES:
                self.assertIn(mod, contract_check.detail)

    def test_empty_service_module_rejects(self) -> None:
        """A listed service module must be non-empty to satisfy governance."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mod in REQUIRED_SERVICE_MODULES:
                p = root / mod
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            service_check = next(
                c
                for c in report.checks
                if c.name == "capability_approval_context_governance_active"
            )
            self.assertFalse(service_check.passed)
            self.assertIn("empty service modules", service_check.detail)
            for mod in REQUIRED_SERVICE_MODULES:
                self.assertIn(mod, service_check.detail)

    def test_syntax_invalid_service_module_rejects(self) -> None:
        """Service module proof is import-free but requires valid Python."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mod in REQUIRED_SERVICE_MODULES:
                p = root / mod
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("def not valid python\n")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            service_check = next(
                c
                for c in report.checks
                if c.name == "capability_approval_context_governance_active"
            )
            self.assertFalse(service_check.passed)
            self.assertIn("syntax-invalid service modules", service_check.detail)
            for mod in REQUIRED_SERVICE_MODULES:
                self.assertIn(mod, service_check.detail)

    def test_missing_replay_classifier_flags_replay_honesty(self) -> None:
        """If the replay classifier module is absent, replay_honesty
        must fail."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = SignoffGate(repo_root=Path(tmp))
            report = gate.evaluate()
            replay_check = next(
                (c for c in report.checks if c.name == "replay_honesty_active"),
                None,
            )
            self.assertIsNotNone(replay_check)
            self.assertFalse(replay_check.passed)


# ---------------------------------------------------------------------------
# Test: gate is fail-closed on partial presence
# ---------------------------------------------------------------------------


class TestSignoffGateFailClosedOnPartialPresence(unittest.TestCase):
    """Prove the gate refuses partial coverage. These tests simulate a
    repo that has SOME but not ALL required artifacts, and assert that
    the gate reports a fail (never a silent partial pass)."""

    def _make_full_tree(self, root: Path) -> None:
        """Create a minimal fake tree that passes every signoff check."""
        # Schemas.
        schema_dir = root / "kernel" / "schemas"
        schema_dir.mkdir(parents=True)
        for name in REQUIRED_SCHEMAS:
            (schema_dir / f"{name}.schema.json").write_text(
                json.dumps(
                    {
                        "type": "object",
                        "schema_version": SCHEMA_FREEZE_TAG,
                    }
                )
            )
        # Contract / service / kernel modules.
        for rel in (
            REQUIRED_CONTRACT_MODULES
            + REQUIRED_SERVICE_MODULES
            + REQUIRED_KERNEL_MODULES
        ):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# stub for signoff gate fake tree\n")
        # Retention declaration: quarantine runner adapter is in
        # REQUIRED_KERNEL_MODULES so it is already created above.
        # Governance baseline docs for invariant coverage declaration.
        gov_const = root / "governance" / "constitution"
        gov_impl = root / "governance" / "implementation"
        gov_const.mkdir(parents=True, exist_ok=True)
        gov_impl.mkdir(parents=True, exist_ok=True)
        (
            gov_const / "sovereign_engineering_operating_system_master_plan_v11.txt"
        ).write_text("stub constitution\n")
        (
            gov_impl / "v11_narrow_path_implementation_foundation.md"
        ).write_text("stub foundation\n")
        (gov_impl / "invariant_bindings.yaml").write_text(
            """---
invariants:
  - invariant_id: INV-TEST
    enforcement_module: "kernel/lifecycle/stage_types.py"
    acceptance_test_ids:
      - "AT-999"
"""
        )
        carrier = (
            root
            / "validation"
            / "tests"
            / "acceptance"
            / "test_at_999_invariant_binding.py"
        )
        carrier.parent.mkdir(parents=True, exist_ok=True)
        carrier.write_text("# stub invariant binding carrier\n")

    def test_full_fake_tree_passes(self) -> None:
        """Control: a fake tree with ALL required artifacts must PASS.

        This proves the gate is correctly wired — not just unconditionally
        failing on throwaway paths."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            self.assertTrue(
                report.all_passed(),
                f"fake full tree should pass; failing: "
                f"{[c.name for c in report.failing()]}",
            )

    def test_removing_one_kernel_module_fails_gate(self) -> None:
        """Removing a single required kernel module must cause fail-closed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            # Remove one required kernel module.
            victim = root / REQUIRED_KERNEL_MODULES[0]
            victim.unlink()

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            self.assertFalse(report.all_passed())
            kernel_check = next(
                c for c in report.checks if c.name == "kernel_modules_present"
            )
            self.assertFalse(kernel_check.passed)
            self.assertIn(REQUIRED_KERNEL_MODULES[0], kernel_check.detail)

    def test_empty_kernel_module_rejects(self) -> None:
        """A listed kernel artifact must be non-empty to satisfy signoff."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            victim = REQUIRED_KERNEL_MODULES[0]
            (root / victim).write_text("")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            kernel_check = next(
                c for c in report.checks if c.name == "kernel_modules_present"
            )
            self.assertFalse(kernel_check.passed)
            self.assertIn("empty kernel modules", kernel_check.detail)
            self.assertIn(victim, kernel_check.detail)

    def test_syntax_invalid_python_kernel_module_rejects(self) -> None:
        """Python kernel artifacts are checked with import-free AST parsing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            victim = REQUIRED_KERNEL_MODULES[0]
            (root / victim).write_text("def not valid python\n")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            kernel_check = next(
                c for c in report.checks if c.name == "kernel_modules_present"
            )
            self.assertFalse(kernel_check.passed)
            self.assertIn("syntax-invalid kernel modules", kernel_check.detail)
            self.assertIn(victim, kernel_check.detail)

    def test_non_python_kernel_artifact_requires_only_non_empty_presence(self) -> None:
        """Non-Python kernel artifacts remain non-empty presence checks only."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            sql_artifact = (
                "kernel/stores/sqlite/migrations/0001_core_signable_path.sql"
            )
            (root / sql_artifact).write_text("not python but non-empty\n")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            kernel_check = next(
                c for c in report.checks if c.name == "kernel_modules_present"
            )
            self.assertTrue(
                kernel_check.passed,
                f"non-Python artifact should not be AST parsed: {kernel_check.detail}",
            )

    def test_removing_constitution_fails_invariant_coverage(self) -> None:
        """Removing the baseline constitution file must fail the invariant
        coverage declaration check (INV-CAP-UI-STATE-IS-NOT-AUTHORITY
        requires the gate to refuse without baseline proof)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            # Remove the constitution.
            (
                root
                / "governance"
                / "constitution"
                / "sovereign_engineering_operating_system_master_plan_v11.txt"
            ).unlink()

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            self.assertFalse(report.all_passed())
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)

    def test_missing_invariant_bindings_fails_invariant_coverage(self) -> None:
        """The first proof-linked signoff check must require the binding
        registry, not only foundation/constitution document presence."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            (
                root
                / "governance"
                / "implementation"
                / "invariant_bindings.yaml"
            ).unlink()

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)
            self.assertIn("missing invariant bindings", inv_check.detail)

    def test_empty_invariant_bindings_fails_invariant_coverage(self) -> None:
        """The invariant proof-link surface must be non-empty."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            (
                root
                / "governance"
                / "implementation"
                / "invariant_bindings.yaml"
            ).write_text("---\ninvariants: []\n")

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)
            self.assertIn("invariant bindings are empty", inv_check.detail)

    def test_binding_without_enforcement_module_fails_invariant_coverage(self) -> None:
        """Every checked invariant binding must name an enforcement module."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            (
                root
                / "governance"
                / "implementation"
                / "invariant_bindings.yaml"
            ).write_text(
                """---
invariants:
  - invariant_id: INV-TEST
    acceptance_test_ids:
      - "AT-999"
"""
            )

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)
            self.assertIn("INV-TEST missing enforcement_module", inv_check.detail)

    def test_binding_without_acceptance_ids_fails_invariant_coverage(self) -> None:
        """Every checked invariant binding must name acceptance-test IDs."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            (
                root
                / "governance"
                / "implementation"
                / "invariant_bindings.yaml"
            ).write_text(
                """---
invariants:
  - invariant_id: INV-TEST
    enforcement_module: "kernel/lifecycle/stage_types.py"
"""
            )

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)
            self.assertIn("INV-TEST missing acceptance_test_ids", inv_check.detail)

    def test_missing_acceptance_carrier_fails_invariant_coverage(self) -> None:
        """Every acceptance-test ID must resolve to an existing carrier file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_full_tree(root)
            (
                root
                / "validation"
                / "tests"
                / "acceptance"
                / "test_at_999_invariant_binding.py"
            ).unlink()

            gate = SignoffGate(repo_root=root)
            report = gate.evaluate()
            inv_check = next(
                c for c in report.checks if c.name == "invariant_coverage_declared"
            )
            self.assertFalse(inv_check.passed)
            self.assertIn("test carrier missing for AT-999", inv_check.detail)


# ---------------------------------------------------------------------------
# Test: gate check-name stability (audit query surface)
# ---------------------------------------------------------------------------


class TestSignoffGateCheckNamesStable(unittest.TestCase):
    """§22.10 audit-query bindings require that the gate's check names be
    stable identifiers. A rename would break any downstream audit query
    that binds to a sign-off decision."""

    #: Canonical check names expected by the §31 slice gate. Any change
    #: to this tuple is a deliberate break and must be reflected in
    #: governance/implementation/invariant_bindings.yaml.
    _EXPECTED_CHECKS: tuple[str, ...] = (
        "frozen_schemas_present",
        "core_contracts_formalized",
        "capability_approval_context_governance_active",
        "kernel_modules_present",
        "replay_honesty_active",
        "context_completeness_active",
        "retention_and_pinning_declared",
        "invariant_coverage_declared",
    )

    def test_expected_checks_present(self) -> None:
        """Every expected check name must be in the gate's output."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        actual = {c.name for c in report.checks}
        for name in self._EXPECTED_CHECKS:
            self.assertIn(name, actual, f"missing expected check: {name}")

    def test_no_unexpected_checks(self) -> None:
        """The gate must not introduce unannounced checks (scope lock)."""
        gate = SignoffGate(repo_root=_REPO_ROOT)
        report = gate.evaluate()
        actual = {c.name for c in report.checks}
        unexpected = actual - set(self._EXPECTED_CHECKS)
        self.assertEqual(
            unexpected, set(),
            f"unexpected checks (scope drift): {unexpected}",
        )


if __name__ == "__main__":
    unittest.main()
