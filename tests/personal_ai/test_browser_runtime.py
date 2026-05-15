import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_runtime import (
    build_optional_browser_smoke_status,
    run_browser_runtime,
)
from kernel.personal_ai.adapters.browser_runtime_boundary import (
    write_browser_runtime_admission_artifacts,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import RuntimeAdmissionDecision


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BrowserRuntimeTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        input_dir.mkdir()
        fixture_path = input_dir / "fixture.html"
        fixture_path.write_text(
            "<html><head><title>Runtime Fixture</title></head><body>"
            "<input name='query' data-seos-allowed-field='true'>"
            "<button id='go' data-seos-allowed-button='true'>Go</button>"
            "</body></html>",
            encoding="utf-8",
        )
        fixture_actions_path = input_dir / "fixture_actions.json"
        write_json_atomically(
            fixture_actions_path,
            {
                "actions": [
                    {"action": "inspect_title"},
                    {
                        "action": "fill_allowed_field",
                        "field_name": "query",
                        "value": "local-only",
                    },
                    {"action": "click_allowed_button", "button_id": "go"},
                ],
                "policy": {"timeout_seconds": 5},
            },
        )
        real_actions_path = input_dir / "real_actions.json"
        write_json_atomically(
            real_actions_path,
            {
                "actions": [
                    {"action": "navigate"},
                    {"action": "inspect_title"},
                    {"action": "capture_screenshot"},
                ]
            },
        )
        return root, fixture_path, fixture_actions_path, real_actions_path

    def test_fixture_runtime_writes_result_manifest_without_real_browser(self):
        root, fixture_path, fixture_actions_path, _ = self.make_root()
        output_dir = root / "fixture-output"
        output_dir.mkdir()

        result = run_browser_runtime(
            output_dir,
            fixture_path=fixture_path,
            actions_path=fixture_actions_path,
        )
        manifest = read_json(result.result_manifest_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_browser_called)
        self.assertTrue(result.action_log_path.exists())
        self.assertTrue(result.evidence_manifest_path.exists())
        self.assertFalse(manifest["real_browser_called"])
        self.assertFalse(manifest["external_network_used"])
        self.assertFalse(manifest["credential_persistence_used"])
        self.assertEqual(manifest["screenshot_evidence_mode"], "dom_metadata_only_fixture")

    def test_real_browser_dry_run_local_url_requires_admission(self):
        root, _, _, real_actions_path = self.make_root()
        output_dir = root / "real-dry-run"
        output_dir.mkdir()
        artifacts = write_browser_runtime_admission_artifacts(root)

        result = run_browser_runtime(
            output_dir,
            target_url="http://127.0.0.1:8123/local-fixture",
            actions_path=real_actions_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        manifest = read_json(result.result_manifest_path)
        dry_run_plan = read_json(result.dry_run_plan_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_browser_called)
        self.assertTrue(manifest["runtime_admission_decision"]["admitted"])
        self.assertFalse(manifest["real_browser_called"])
        self.assertFalse(manifest["playwright_runtime_used"])
        self.assertFalse(manifest["selenium_runtime_used"])
        self.assertFalse(manifest["external_network_used"])
        self.assertFalse(manifest["credential_persistence_used"])
        self.assertFalse(manifest["real_screenshot_captured"])
        self.assertFalse(dry_run_plan["network_used"])

    def test_external_url_is_denied_and_quarantined(self):
        root, _, _, real_actions_path = self.make_root()
        output_dir = root / "external-denied"
        output_dir.mkdir()
        artifacts = write_browser_runtime_admission_artifacts(root)

        result = run_browser_runtime(
            output_dir,
            target_url="https://example.com",
            actions_path=real_actions_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_browser_called"])
        self.assertFalse(failure["external_network_used"])
        self.assertIn("external browser target_url", failure["error_message"])

    def test_sensitive_real_browser_action_is_denied(self):
        root, _, _, _ = self.make_root()
        output_dir = root / "sensitive-denied"
        output_dir.mkdir()
        actions_path = root / "input" / "sensitive_actions.json"
        write_json_atomically(
            actions_path,
            {"actions": [{"action": "navigate", "intent": "login"}]},
        )
        artifacts = write_browser_runtime_admission_artifacts(root)

        result = run_browser_runtime(
            output_dir,
            target_url="http://localhost:8123",
            actions_path=actions_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["credential_persistence_used"])
        self.assertIn("sensitive browser action", failure["error_message"])

    def test_missing_admission_denies_real_browser_dry_run(self):
        root, _, _, real_actions_path = self.make_root()
        output_dir = root / "missing-admission"
        output_dir.mkdir()

        result = run_browser_runtime(
            output_dir,
            target_url="http://localhost:8123",
            actions_path=real_actions_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertIn("admission denied", failure["error_message"])
        self.assertFalse(failure["real_browser_called"])

    def test_optional_browser_smoke_stays_disabled_without_activation_allowed(self):
        decision = RuntimeAdmissionDecision(
            decision_type="personal_ai_runtime_admission_decision_v1",
            adapter_id="real_browser_runtime_boundary",
            capability="drive_real_browser_with_allowlist",
            runtime_class="external_browser",
            admitted=True,
            activation_allowed=False,
            dry_run=True,
            reason_codes=(),
            artifact_hashes={},
            manifest_hash_bound=True,
            runtime_class_policy={},
            activation_sources=("human_approval_artifact",),
        )

        status = build_optional_browser_smoke_status(
            "http://127.0.0.1:8123",
            decision,
            environ={"SEOS_ENABLE_BROWSER_SMOKE": "true"},
        )

        self.assertFalse(status["enabled"])
        self.assertTrue(status["explicit_env_enabled"])
        self.assertTrue(status["target_url_is_loopback"])
        self.assertFalse(status["real_browser_called"])


if __name__ == "__main__":
    unittest.main()
