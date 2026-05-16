import json
import tempfile
import unittest
from pathlib import Path

from kernel.evidence.sealed_redaction_contract import validate_sealed_evidence_record
from kernel.personal_ai.model_provider_real_smoke_manual_run import (
    ModelProviderManualSmokeRunResult,
    build_model_provider_manual_smoke_run,
    build_model_provider_smoke_sealed_evidence_payload,
    write_model_provider_manual_smoke_run,
)


class ModelProviderManualSmokeRunTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def enabled_env(self):
        return {
            "SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH": "true",
            "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
            "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true",
            "OPENAI_API_KEY": "sk-test-secret-value-must-not-leak",
        }

    def test_builds_ready_manual_run_without_runtime_execution_or_secret_leak(self):
        result = build_model_provider_manual_smoke_run(
            environ=self.enabled_env(),
            prompt_text="Return the word ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=16,
            temperature=0.0,
            request_id="manual-smoke-001",
            expected_response_contract={"kind": "text", "max_chars": 64},
        )

        self.assertIsInstance(result, ModelProviderManualSmokeRunResult)
        self.assertTrue(result.complete)
        self.assertTrue(result.ready_for_manual_execution)
        self.assertFalse(result.runtime_execution_performed)
        self.assertFalse(result.model_api_called)
        self.assertFalse(result.secret_value_read)
        self.assertFalse(result.secret_value_persisted)
        self.assertTrue(result.required_human_approval)
        report = result.report
        self.assertEqual(report["status"], "manual_model_provider_smoke_run_planned_no_runtime_execution")
        self.assertEqual(report["provider_name"], "openai")
        self.assertEqual(report["model_name"], "gpt-test")
        self.assertNotIn("sk-test-secret-value-must-not-leak", json.dumps(report, sort_keys=True))
        self.assertFalse(report["secret_value_read"])
        self.assertFalse(report["secret_value_persisted"])
        self.assertFalse(report["secret_value_serialized"])
        self.assertFalse(report["raw_prompt_persisted"])
        self.assertFalse(report["raw_provider_response_persisted"])
        self.assertFalse(report["runtime_execution_performed"])
        self.assertFalse(report["model_api_called"])
        self.assertFalse(report["external_network_accessed"])
        self.assertFalse(report["file_or_tool_action_performed"])
        self.assertFalse(report["output_triggered_tool_or_file_authority"])
        self.assertFalse(report["automatic_runtime_authority_granted"])

    def test_sealed_evidence_payload_is_embedded_and_contract_valid(self):
        result = build_model_provider_manual_smoke_run(
            environ=self.enabled_env(),
            prompt_text="Return the word ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=16,
            temperature=0.0,
            request_id="manual-smoke-sealed-001",
        )

        sealed_payload = result.report["sealed_evidence_payload"]
        self.assertEqual(sealed_payload["evidence_contract"], "sealed_redaction_v1")
        evidence = sealed_payload["evidence"]
        validation = validate_sealed_evidence_record(evidence)
        self.assertTrue(validation.accepted, validation.failures)
        self.assertEqual(evidence["classification"], "secret")
        self.assertEqual(evidence["representation"], "redacted_digest")
        self.assertTrue(str(evidence["digest"]).startswith("sha256:"))
        evidence_payload = evidence["payload"]
        self.assertEqual(evidence_payload["request_id"], "manual-smoke-sealed-001")
        self.assertFalse(evidence_payload["raw_prompt_persisted"])
        self.assertFalse(evidence_payload["raw_provider_response_persisted"])
        self.assertFalse(evidence_payload["runtime_execution_performed"])
        self.assertFalse(evidence_payload["model_api_called"])
        self.assertFalse(evidence_payload["secret_value_read"])
        self.assertFalse(evidence_payload["secret_value_persisted"])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(evidence, sort_keys=True))
        self.assertNotIn("sk-test-secret-value-must-not-leak", json.dumps(evidence, sort_keys=True))
        self.assertNotIn("Return the word ok.", json.dumps(evidence, sort_keys=True))

    def test_build_model_provider_smoke_sealed_evidence_payload_rejects_raw_prompt(self):
        report = {
            "request_id": "manual-smoke-bad",
            "provider_name": "openai",
            "model_name": "gpt-test",
            "prompt_sha256": "a" * 64,
            "prompt_length_chars": 16,
            "manual_flags": {},
            "secret_presence": {},
            "secret_value_read": False,
            "secret_value_persisted": False,
            "secret_value_serialized": False,
            "raw_prompt_persisted": True,
            "raw_provider_response_persisted": False,
            "runtime_execution_performed": False,
            "model_api_called": False,
            "external_network_accessed": False,
            "file_or_tool_action_performed": False,
            "output_triggered_tool_or_file_authority": False,
            "automatic_runtime_authority_granted": False,
            "required_human_approval": True,
        }

        with self.assertRaisesRegex(ValueError, "raw_prompt_persisted must be false"):
            build_model_provider_smoke_sealed_evidence_payload(report)

    def test_missing_manual_flags_and_secret_block_readiness(self):
        result = build_model_provider_manual_smoke_run(
            environ={},
            prompt_text="Return ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=16,
            temperature=0.0,
            request_id="manual-smoke-002",
        )

        self.assertFalse(result.ready_for_manual_execution)
        failures = result.report["failures"]
        self.assertIn("SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH_missing_or_not_true", failures)
        self.assertIn("SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE_missing_or_not_true", failures)
        self.assertIn("SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT_missing_or_not_true", failures)
        self.assertIn("OPENAI_API_KEY_missing", failures)
        self.assertFalse(result.report["runtime_execution_performed"])
        self.assertFalse(result.report["model_api_called"])

    def test_forbidden_contract_actions_block_readiness(self):
        result = build_model_provider_manual_smoke_run(
            environ=self.enabled_env(),
            prompt_text="Return ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=16,
            temperature=0.0,
            request_id="manual-smoke-003",
            expected_response_contract={
                "kind": "text",
                "tool_calls": [],
                "file_edits": [],
                "browser_actions": [],
            },
        )

        self.assertFalse(result.ready_for_manual_execution)
        self.assertIn("tool_calls_forbidden", result.report["failures"])
        self.assertIn("file_edits_forbidden", result.report["failures"])
        self.assertIn("browser_actions_forbidden", result.report["failures"])
        self.assertFalse(result.report["output_triggered_tool_or_file_authority"])

    def test_writes_report_atomically_and_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        result = write_model_provider_manual_smoke_run(
            output_dir=output_dir,
            environ=self.enabled_env(),
            prompt_text="Return ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=16,
            temperature=0.0,
            request_id="manual-smoke-004",
        )

        self.assertTrue(result.report_path.is_file())
        payload = json.loads(result.report_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["report_type"], "personal_ai_model_provider_real_smoke_manual_run_v1")
        self.assertTrue(payload["ready_for_manual_execution"])
        self.assertNotIn("Return ok.", json.dumps(payload, sort_keys=True))
        self.assertIn("prompt_sha256", payload)
        self.assertIn("sealed_evidence_payload", payload)
        with self.assertRaisesRegex(ValueError, "already exists"):
            write_model_provider_manual_smoke_run(
                output_dir=output_dir,
                environ=self.enabled_env(),
                prompt_text="Return ok.",
                provider_name="openai",
                model_name="gpt-test",
                max_output_tokens=16,
                temperature=0.0,
                request_id="manual-smoke-005",
            )

    def test_output_dir_must_exist(self):
        output_dir = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            write_model_provider_manual_smoke_run(
                output_dir=output_dir / "missing",
                environ=self.enabled_env(),
                prompt_text="Return ok.",
                provider_name="openai",
                model_name="gpt-test",
                max_output_tokens=16,
                temperature=0.0,
                request_id="manual-smoke-006",
            )

    def test_invalid_numeric_inputs_are_failures_not_runtime(self):
        result = build_model_provider_manual_smoke_run(
            environ=self.enabled_env(),
            prompt_text="Return ok.",
            provider_name="openai",
            model_name="gpt-test",
            max_output_tokens=0,
            temperature=3.0,
            request_id="manual-smoke-007",
        )
        self.assertFalse(result.ready_for_manual_execution)
        self.assertIn("max_output_tokens_must_be_positive", result.report["failures"])
        self.assertIn("temperature_out_of_range", result.report["failures"])
        self.assertFalse(result.report["runtime_execution_performed"])
        self.assertFalse(result.report["model_api_called"])

    def test_module_does_not_contain_runtime_or_secret_leak_markers(self):
        source = Path("kernel/personal_ai/model_provider_real_smoke_manual_run.py").read_text(
            encoding="utf-8"
        )
        forbidden_markers = (
            "openai.",
            "requests.",
            "httpx.",
            "urllib",
            "socket.",
            "subprocess",
            "os.system",
            "browser",
            "chromium.launch",
            "write_text(prompt_text",
            "OPENAI_API_KEY]",
            "environ.get(\"OPENAI_API_KEY\")",
            "checkpoint_executed = True",
            "wal_truncate_executed = True",
            "sqlite_state_mutated = True",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, source)

    def test_decision_doc_exists_and_records_manual_only_posture(self):
        text = Path("docs/decisions/model_provider_real_smoke_manual_run_v1.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "MODEL_PROVIDER_REAL_SMOKE_MANUAL_RUN_READY_FOR_LOCAL_TESTS",
            "manual only",
            "default disabled",
            "no model API call",
            "no secret persistence",
            "no output-triggered tool or file authority",
            "Human Review Required",
            "sealed evidence payload",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
