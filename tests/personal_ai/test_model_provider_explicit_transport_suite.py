import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_provider_activation_package import (
    build_model_provider_activation_package,
)
from kernel.personal_ai.adapters.model_provider_live_smoke import (
    build_disabled_model_provider_live_smoke_plan,
)
from kernel.personal_ai.adapters.model_provider_disabled_live_smoke_runner import (
    run_model_provider_disabled_live_smoke,
)
from kernel.personal_ai.adapters.model_provider_transport_adapter import (
    build_live_smoke_transport_request,
    validate_transport_request,
    validate_transport_response,
    write_transport_validation_report,
)
from kernel.personal_ai.adapters.openai_explicit_transport import (
    build_openai_explicit_transport,
    run_openai_explicit_transport,
)


class ModelProviderExplicitTransportSuiteTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def build_live_smoke_plan(self, root: Path) -> Path:
        activation_dir = root / "activation"
        smoke_dir = root / "smoke_plan"
        activation_dir.mkdir()
        smoke_dir.mkdir()
        build_model_provider_activation_package(
            activation_dir,
            provider_id="openai",
            schema_name="job_route_classification_v1",
            reviewer_id="reviewer-1",
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        )
        return build_disabled_model_provider_live_smoke_plan(
            activation_dir,
            smoke_dir,
            provider_id="openai",
            api_key_env_var="OPENAI_API_KEY",
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        ).plan_path

    def test_transport_contract_validates_request_and_response(self):
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="a" * 64,
        )
        self.assertTrue(validate_transport_request(request)["complete"])
        self.assertFalse(request["tool_calls_allowed"])
        self.assertFalse(request["file_edits_allowed"])
        self.assertFalse(request["raw_prompt_contains_secret"])

        response = {
            "status": "ok",
            "provider_id": "openai",
            "tool_call_requested": False,
            "file_edit_requested": False,
            "raw_provider_response_persisted": False,
        }
        self.assertTrue(
            validate_transport_response(response, provider_id="openai")["complete"]
        )

    def test_transport_contract_rejects_tool_and_file_authority(self):
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="b" * 64,
        )
        request["tool_calls_allowed"] = True
        request["file_edits_allowed"] = True

        validation = validate_transport_request(request)

        self.assertFalse(validation["complete"])
        self.assertIn("tool_calls_must_be_false", validation["failures"])
        self.assertIn("file_edits_must_be_false", validation["failures"])

    def test_writes_transport_validation_report_without_network(self):
        output_dir = self.make_output_dir()
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="c" * 64,
        )
        response = {"status": "ok", "provider_id": "openai"}

        report = write_transport_validation_report(
            output_dir / "transport_validation.json",
            request=request,
            response=response,
        )

        self.assertTrue(report["complete"])
        self.assertFalse(report["network_performed_by_validator"])
        self.assertFalse(report["api_key_value_persisted"])
        self.assertFalse(report["api_key_value_logged"])
        self.assertFalse(report["raw_provider_response_persisted"])

    def test_openai_transport_is_disabled_by_default(self):
        output_dir = self.make_output_dir()
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="d" * 64,
        )
        result = run_openai_explicit_transport(
            request,
            output_dir,
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        )

        self.assertEqual(result.status, "disabled_by_callsite")
        self.assertFalse(result.network_call_performed)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["http_transport_called"])
        self.assertFalse(payload["network_call_performed"])
        self.assertNotIn("secret-not-persisted", result.result_path.read_text(encoding="utf-8"))

    def test_openai_transport_requires_env_flag_and_key_and_http_transport(self):
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="e" * 64,
        )

        no_flag_dir = self.make_output_dir()
        no_flag = run_openai_explicit_transport(
            request,
            no_flag_dir,
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
            allow_network=True,
            http_transport=lambda payload, key: {"status": "ok", "provider_id": "openai"},
        )
        self.assertEqual(no_flag.status, "disabled_by_environment_flag")
        self.assertFalse(no_flag.network_call_performed)

        no_key_dir = self.make_output_dir()
        no_key = run_openai_explicit_transport(
            request,
            no_key_dir,
            environ={"SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true"},
            allow_network=True,
            http_transport=lambda payload, key: {"status": "ok", "provider_id": "openai"},
        )
        self.assertEqual(no_key.status, "missing_openai_api_key")
        self.assertFalse(no_key.network_call_performed)

        no_transport_dir = self.make_output_dir()
        no_transport = run_openai_explicit_transport(
            request,
            no_transport_dir,
            environ={
                "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_network=True,
        )
        self.assertEqual(no_transport.status, "missing_explicit_http_transport")
        self.assertFalse(no_transport.network_call_performed)

    def test_openai_transport_uses_injected_http_transport_only_after_all_gates(self):
        output_dir = self.make_output_dir()
        request = build_live_smoke_transport_request(
            provider_id="openai",
            plan_sha256="f" * 64,
        )
        calls = []

        def http_transport(payload, api_key):
            calls.append((payload, api_key))
            self.assertEqual(api_key, "secret-not-persisted")
            self.assertEqual(payload["tools"], [])
            return {"status": "ok", "provider_id": "openai"}

        result = run_openai_explicit_transport(
            request,
            output_dir,
            environ={
                "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_network=True,
            http_transport=http_transport,
        )

        self.assertEqual(result.status, "completed_via_explicit_http_transport")
        self.assertTrue(result.network_call_performed)
        self.assertEqual(len(calls), 1)
        result_text = result.result_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-not-persisted", result_text)
        payload = json.loads(result_text)
        self.assertFalse(payload["api_key_value_persisted"])
        self.assertFalse(payload["api_key_value_logged"])
        self.assertFalse(payload["tool_calls_allowed"])
        self.assertFalse(payload["file_edits_allowed"])
        self.assertTrue(payload["response_validation"]["complete"])

    def test_runner_can_use_openai_explicit_transport_adapter_as_injected_transport(self):
        root = self.make_output_dir()
        plan_path = self.build_live_smoke_plan(root)
        runner_dir = root / "runner"
        runner_dir.mkdir()
        transport_dir = root / "transport"
        transport_dir.mkdir()

        def live_transport(request):
            transport_result = run_openai_explicit_transport(
                request,
                transport_dir,
                environ={
                    "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true",
                    "OPENAI_API_KEY": "secret-not-persisted",
                },
                allow_network=True,
                http_transport=lambda payload, key: {
                    "status": "ok",
                    "provider_id": "openai",
                },
            )
            self.assertEqual(
                transport_result.status,
                "completed_via_explicit_http_transport",
            )
            return {"status": "ok", "provider_id": "openai"}

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            runner_dir,
            environ={
                "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_live_smoke=True,
            live_transport=live_transport,
        )

        self.assertEqual(result.status, "completed_via_explicit_transport")
        self.assertTrue(result.live_provider_called)
        runner_text = result.result_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-not-persisted", runner_text)
        transport_report = json.loads(
            (transport_dir / "openai_explicit_transport_result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(transport_report["response_validation"]["complete"])
        self.assertFalse(transport_report["api_key_value_persisted"])
        self.assertFalse(transport_report["api_key_value_logged"])

    def test_openai_transport_descriptor_is_disabled_by_default(self):
        descriptor = build_openai_explicit_transport()

        self.assertFalse(descriptor["enabled_by_default"])
        self.assertTrue(descriptor["requires_callsite_allow"])
        self.assertEqual(
            descriptor["requires_environment_flag"],
            "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT",
        )
        self.assertFalse(descriptor["api_key_value_persisted"])
        self.assertFalse(descriptor["api_key_value_logged"])
        self.assertFalse(descriptor["tool_calls_allowed"])
        self.assertFalse(descriptor["file_edits_allowed"])


if __name__ == "__main__":
    unittest.main()
