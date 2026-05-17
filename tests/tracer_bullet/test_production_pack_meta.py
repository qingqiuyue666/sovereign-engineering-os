"""Production pack meta tests — verify all stage artifacts exist and are clean.

Tests that every stage in the production pack has:
- generator script
- generated module
- registry JSON
- policy JSON
- runbook MD
- test file

Also verifies no generated module contains forbidden imports or strings.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STAGE_IDS = [
    "patch_application_pipeline",
    "local_execution_kernel",
    "evidence_vault_foundation",
    "replay_engine_foundation",
    "provider_transport_boundary",
    "operator_daily_run_foundation",
    "alert_delivery_foundation",
    "osint_ingestion_foundation",
    "asset_mapping_foundation",
    "decision_engine_foundation",
    "recovery_rollback_foundation",
    "checkpoint_runtime_foundation",
    "run_ledger_hardening_foundation",
    "evidence_index_foundation",
    "decision_report_foundation",
    "local_operator_cli_extension_foundation",
]

FORBIDDEN_IMPORTS = {"subprocess", "socket", "requests", "http.client", "urllib.request", "urllib"}
FORBIDDEN_STRINGS = ["cloud_ai", "push main", "merge main", "branch delete",
                     "live_broker", "live_exchange", "real_trade", "production_deploy"]


class ProductionPackMetaTests(unittest.TestCase):

    # ── generator scripts ──────────────────────────────────────────

    def test_all_generator_scripts_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generate_{sid}.py"
            self.assertTrue(path.is_file(), f"Missing generator: {path}")

    # ── generated modules ──────────────────────────────────────────

    def test_all_generated_modules_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            self.assertTrue(path.is_file(), f"Missing generated module: {path}")

    def test_all_generated_modules_syntax_valid(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source)
            except SyntaxError as e:
                self.fail(f"Syntax error in {sid}: {e}")

    # ── policies ──────────────────────────────────────────────────

    def test_all_policies_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "governance" / "security" / f"{sid}_policy_v1.json"
            self.assertTrue(path.is_file(), f"Missing policy: {path}")

    # ── registries ────────────────────────────────────────────────

    def test_all_registries_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "governance" / "local_train" / f"{sid}_registry_v1.json"
            self.assertTrue(path.is_file(), f"Missing registry: {path}")

    # ── runbooks ──────────────────────────────────────────────────

    def test_all_runbooks_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "docs" / "runbooks" / f"{sid}_v1.md"
            self.assertTrue(path.is_file(), f"Missing runbook: {path}")

    # ── tests ─────────────────────────────────────────────────────

    def test_all_tests_exist(self):
        for sid in STAGE_IDS:
            path = ROOT / "tests" / "tracer_bullet" / f"test_{sid}.py"
            self.assertTrue(path.is_file(), f"Missing test: {path}")

    # ── forbidden imports ─────────────────────────────────────────

    def test_no_generated_module_has_forbidden_imports(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_IMPORTS:
                pattern = f"import {forbidden}"
                self.assertNotIn(pattern, source, f"{sid} imports forbidden {forbidden}")
                pattern2 = f"from {forbidden}"
                self.assertNotIn(pattern2, source, f"{sid} imports from forbidden {forbidden}")

    # ── forbidden strings ─────────────────────────────────────────

    def test_no_generated_module_has_forbidden_strings(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            source_lower = source.lower()
            for forbidden in FORBIDDEN_STRINGS:
                self.assertNotIn(forbidden, source_lower, f"{sid} contains {forbidden}")

    # ── dataclass receipt check ────────────────────────────────────

    def test_every_generated_module_has_receipt_dataclass(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            self.assertIn("@dataclass", source, f"{sid} missing @dataclass decorator")
            self.assertIn("Receipt", source, f"{sid} missing Receipt class")

    # ── validate function check ────────────────────────────────────

    def test_every_generated_module_has_at_least_one_validate_function(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            self.assertIn("def validate_", source, f"{sid} missing validate_ function")

    # ── produce receipt function check ─────────────────────────────

    def test_every_generated_module_has_produce_receipt_function(self):
        for sid in STAGE_IDS:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            source = path.read_text(encoding="utf-8")
            self.assertIn("def produce_", source, f"{sid} missing produce_ function")


class StagePackCoverFilesTest(unittest.TestCase):

    def test_cover_policy_exists(self):
        path = ROOT / "governance" / "security" / "production_code_stage_pack_policy_v1.json"
        self.assertTrue(path.is_file())

    def test_cover_registry_exists(self):
        path = ROOT / "governance" / "local_train" / "production_code_stage_pack_v1.json"
        self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
