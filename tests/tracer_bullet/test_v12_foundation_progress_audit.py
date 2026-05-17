import json
import unittest
from pathlib import Path


class V12FoundationProgressAuditTests(unittest.TestCase):
    def test_progress_audit_records_implemented_and_forbidden_surfaces(self):
        path = Path("governance/v12/v12_foundation_progress_audit_v1.json")
        self.assertTrue(path.is_file(), str(path))
        audit = json.loads(path.read_text(encoding="utf-8"))
        for surface in (
            "core_secret_scanner",
            "dry_run_runner",
            "replay_verifier",
            "provider_mock_contract",
            "telegram_mock_contract",
            "vault_keyring_contracts",
            "daemon_scheduler_contracts",
            "domain_pipeline_contracts",
            "dashboard_data_model",
        ):
            self.assertIn(surface, audit["implemented_surfaces"])
        forbidden = audit["forbidden_surfaces_not_implemented"]
        for flag in (
            "live_provider_runtime",
            "network_accessed",
            "secret_value_read",
            "secret_value_persisted",
            "live_telegram",
            "real_vault",
            "kms_keyring_runtime",
            "daemon_runtime",
            "osint_live_ingestion",
            "dashboard_runtime",
            "real_wal_reader",
            "real_sqlite_migration",
        ):
            self.assertIs(forbidden[flag], True)
        self.assertIn("v12-foundation-hardening-v1", audit["next_allowed_branches"])

    def test_runbook_and_decision_exist(self):
        for path in (
            Path("docs/runbooks/v12_foundation_overnight_build_v1.md"),
            Path("docs/decisions/v12_foundation_overnight_build_v1.md"),
        ):
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("V12 Foundation", text)
            self.assertIn("no live provider", text)


if __name__ == "__main__":
    unittest.main()
