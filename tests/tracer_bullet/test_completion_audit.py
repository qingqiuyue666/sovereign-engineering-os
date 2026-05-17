"""Completion audit tracer-bullet tests.

Tests the completion audit layer hardening:
- no category exceeds 100
- production autonomy is 0 / false
- real provider execution remains 0 / false
- overall operational completion remains below production-ready threshold
- report says descriptor-level foundation, not production runtime
- missing gate evidence lowers confidence
- no overclaim language
- deterministic output
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.status.completion_audit import (
    CompletionAuditReport,
    produce_completion_audit,
)

AUDIT_PATH = Path("governance/v12/runtime_integration_completion_audit_v1.json")


class CompletionAuditPolicyTests(unittest.TestCase):
    """Policy/audit JSON integrity tests."""

    def test_audit_file_exists_and_is_valid_json(self):
        self.assertTrue(AUDIT_PATH.is_file(), f"Audit file missing: {AUDIT_PATH}")
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(audit["audit_type"], "runtime_integration_completion_audit_v1")
        self.assertEqual(audit["version"], "v1")
        self.assertFalse(audit["claim_production_runtime_complete"])
        self.assertFalse(audit["claim_production_autonomy_complete"])
        self.assertFalse(audit["runtime_execution_performed"])
        self.assertFalse(audit["network_accessed"])
        self.assertFalse(audit["secret_value_read"])
        self.assertFalse(audit["secret_value_persisted"])
        self.assertFalse(audit["provider_execution_performed"])
        self.assertFalse(audit["real_vault_write_performed"])


class CompletionAuditAcceptanceTests(unittest.TestCase):
    """Happy-path acceptance tests."""

    def test_valid_audit_accepted(self):
        report = produce_completion_audit()
        self.assertIsInstance(report, CompletionAuditReport)
        self.assertTrue(report.accepted, f"Expected accepted but got: {report.failures}")
        self.assertEqual(report.failures, ())

    def test_no_category_exceeds_100(self):
        report = produce_completion_audit()
        for name, value in report.categories.items():
            self.assertLessEqual(value, 100, f"{name} exceeds 100%: {value}")

    def test_production_autonomy_is_zero(self):
        report = produce_completion_audit()
        self.assertEqual(report.categories["production_autonomy_percent"], 0)
        self.assertFalse(report.constraints["production_autonomy_enabled"])

    def test_real_provider_execution_is_zero(self):
        report = produce_completion_audit()
        self.assertEqual(report.categories["real_provider_execution_percent"], 0)
        self.assertFalse(report.constraints["live_provider_execution_enabled"])

    def test_overall_operational_completion_below_production_ready(self):
        report = produce_completion_audit()
        self.assertLess(report.overall_operational_completion_percent, 100)
        self.assertLess(report.overall_operational_completion_percent, 70)

    def test_verdict_says_descriptor_level_not_production(self):
        report = produce_completion_audit()
        self.assertIn("DESCRIPTOR_LEVEL", report.verdict)
        self.assertIn("DRY_RUN_ONLY", report.verdict)
        self.assertNotIn("PRODUCTION", report.verdict)
        self.assertNotIn("100_PERCENT", report.verdict)

    def test_all_dry_run_categories_are_100(self):
        report = produce_completion_audit()
        dry_run_categories = [
            "governance_contract_completion_percent",
            "leak_prevention_foundation_percent",
            "security_truth_substrate_percent",
            "operator_task_ledger_percent",
            "operator_cli_percent",
            "runtime_runner_event_journal_percent",
            "failurebundle_replay_foundation_percent",
            "evidence_vault_boundary_percent",
            "provider_execution_plane_boundary_percent",
            "runtime_integration_hardening_percent",
        ]
        for cat in dry_run_categories:
            self.assertEqual(report.categories[cat], 100, f"{cat} should be 100%")

    def test_all_disabled_categories_are_zero(self):
        report = produce_completion_audit()
        disabled_categories = [
            "real_provider_execution_percent",
            "real_evidence_vault_percent",
            "real_replay_execution_percent",
            "daemon_runtime_percent",
            "dashboard_runtime_percent",
            "production_autonomy_percent",
        ]
        for cat in disabled_categories:
            self.assertEqual(report.categories[cat], 0, f"{cat} should be 0%")

    def test_deterministic_output(self):
        r1 = produce_completion_audit()
        r2 = produce_completion_audit()
        self.assertEqual(r1.as_dict(), r2.as_dict())
        self.assertEqual(r1.report_digest, r2.report_digest)

    def test_report_as_dict_exports_all_fields(self):
        report = produce_completion_audit()
        d = report.as_dict()
        self.assertIn("accepted", d)
        self.assertIn("categories", d)
        self.assertIn("constraints", d)
        self.assertIn("overall_operational_completion_percent", d)
        self.assertIn("verdict", d)
        self.assertIn("report_digest", d)
        self.assertTrue(d["report_digest"].startswith("sha256:"))


class CompletionAuditRejectionTests(unittest.TestCase):
    """Rejection / constraint violation tests."""

    def test_missing_gate_evidence_lowers_confidence(self):
        report = produce_completion_audit(gate_evidence={})
        self.assertFalse(report.accepted)
        failure_msgs = " ".join(report.failures)
        self.assertIn("missing_gate_evidence", failure_msgs)

    def test_partial_gate_evidence_lowers_confidence(self):
        report = produce_completion_audit(gate_evidence={
            "test-runtime-execution-descriptor": True,
        })
        self.assertFalse(report.accepted)
        failure_msgs = " ".join(report.failures)
        self.assertIn("missing_gate_evidence", failure_msgs)

    def test_full_gate_evidence_passes(self):
        report = produce_completion_audit(gate_evidence={
            "test-runtime-execution-descriptor": True,
            "test-dry-run-orchestrator": True,
            "test-runtime-integration-trace": True,
            "test-completion-audit": True,
        })
        self.assertTrue(report.accepted, f"Expected accepted but got: {report.failures}")

    def test_overall_below_100(self):
        report = produce_completion_audit()
        self.assertLess(report.overall_operational_completion_percent, 100)


class CompletionAuditSideEffectFreeTests(unittest.TestCase):
    """Side-effect freedom tests."""

    def test_produce_completion_audit_is_repeatable(self):
        r1 = produce_completion_audit()
        r2 = produce_completion_audit()
        self.assertEqual(r1.as_dict(), r2.as_dict())

    def test_no_network_imports(self):
        import kernel.status.completion_audit as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("requests", content)
            self.assertNotIn("urllib", content)

    def test_no_sqlite_import(self):
        import kernel.status.completion_audit as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("sqlite3", content)
