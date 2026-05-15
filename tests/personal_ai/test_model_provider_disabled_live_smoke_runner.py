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


class ModelProviderDisabledLiveSmokeRunnerTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def build_plan(self, root: Path) -> Path:
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
        result = build_disabled_model_provider_live_smoke_plan(
            activation_dir,
            smoke_dir,
            provider_id="openai",
            api_key_env_var="OPENAI_API_KEY",
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        )
        return result.plan_path

    def test_denies_by_default_without_calling_transport(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        )

        self.assertEqual(result.status, "disabled_by_callsite")
        self.assertFalse(result.live_provider_called)
        self.assertFalse(result.network_used_by_runner)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["live_provider_called"])
        self.assertFalse(payload["network_used_by_runner"])
        self.assertNotIn("secret-not-persisted", result.result_path.read_text(encoding="utf-8"))

    def test_denies_without_environment_enable_flag(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
            allow_live_smoke=True,
            live_transport=lambda request: {"status": "ok", "provider_id": "openai"},
        )

        self.assertEqual(result.status, "disabled_by_environment_flag")
        self.assertFalse(result.live_provider_called)

    def test_denies_without_api_key(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={"SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true"},
            allow_live_smoke=True,
            live_transport=lambda request: {"status": "ok", "provider_id": "openai"},
        )

        self.assertEqual(result.status, "missing_environment_api_key")
        self.assertFalse(result.live_provider_called)

    def test_denies_without_explicit_transport(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={
                "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_live_smoke=True,
        )

        self.assertEqual(result.status, "missing_explicit_live_transport")
        self.assertFalse(result.live_provider_called)

    def test_allows_injected_transport_only_after_all_gates(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()
        calls = []

        def transport(request):
            calls.append(request)
            self.assertFalse(request["tool_calls_allowed"])
            self.assertFalse(request["file_edits_allowed"])
            self.assertFalse(request["raw_prompt_contains_secret"])
            return {"status": "ok", "provider_id": "openai"}

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={
                "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_live_smoke=True,
            live_transport=transport,
        )

        self.assertEqual(result.status, "completed_via_explicit_transport")
        self.assertTrue(result.live_provider_called)
        self.assertFalse(result.network_used_by_runner)
        self.assertEqual(len(calls), 1)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["live_transport_called"])
        self.assertTrue(payload["live_provider_called"])
        self.assertFalse(payload["network_used_by_runner"])
        self.assertFalse(payload["api_key_value_persisted"])
        self.assertFalse(payload["api_key_value_logged"])
        self.assertTrue(payload["schema_validation"]["complete"])
        self.assertNotIn("secret-not-persisted", result.result_path.read_text(encoding="utf-8"))

    def test_transport_response_requesting_tool_call_is_not_complete(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        output_dir = root / "runner"
        output_dir.mkdir()

        result = run_model_provider_disabled_live_smoke(
            plan_path,
            output_dir,
            environ={
                "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
                "OPENAI_API_KEY": "secret-not-persisted",
            },
            allow_live_smoke=True,
            live_transport=lambda request: {
                "status": "ok",
                "provider_id": "openai",
                "tool_call_requested": True,
            },
        )

        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["schema_validation"]["complete"])
        self.assertIn("tool_call_requested", payload["schema_validation"]["failures"])

    def test_malformed_plan_fails_closed(self):
        root = self.make_output_dir()
        output_dir = root / "runner"
        output_dir.mkdir()
        bad_plan = root / "bad_plan.json"
        bad_plan.write_text("{bad", encoding="utf-8")

        result = run_model_provider_disabled_live_smoke(
            bad_plan,
            output_dir,
            environ={},
            allow_live_smoke=True,
        )

        self.assertEqual(result.status, "failed_closed")
        self.assertFalse(result.live_provider_called)
        self.assertIsNotNone(result.failure_path)


if __name__ == "__main__":
    unittest.main()
