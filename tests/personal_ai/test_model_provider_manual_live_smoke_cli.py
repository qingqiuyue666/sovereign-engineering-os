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
from kernel.personal_ai.model_provider_manual_live_smoke_cli import (
    main,
    run_manual_model_provider_live_smoke,
)


class ModelProviderManualLiveSmokeCliTests(unittest.TestCase):
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
        return build_disabled_model_provider_live_smoke_plan(
            activation_dir,
            smoke_dir,
            provider_id="openai",
            api_key_env_var="OPENAI_API_KEY",
            environ={"OPENAI_API_KEY": "secret-not-persisted"},
        ).plan_path

    def test_rejects_missing_exact_confirm_flags(self):
        output_dir = self.make_output_dir()
        plan_path = self.build_plan(output_dir)
        run_dir = output_dir / "run"
        run_dir.mkdir()

        with self.assertRaisesRegex(ValueError, "--allow-network"):
            run_manual_model_provider_live_smoke(
                plan_path=plan_path,
                output_dir=run_dir,
                provider="openai",
                allow_live_smoke=True,
                allow_network=False,
                confirm_manual_live_smoke=True,
                use_stdlib_openai_transport=True,
            )

    def test_cli_rejects_false_flag_without_live_call(self):
        output_dir = self.make_output_dir()
        plan_path = self.build_plan(output_dir)
        run_dir = output_dir / "run"
        run_dir.mkdir()

        exit_code = main(
            [
                "--plan-path",
                plan_path.as_posix(),
                "--output-dir",
                run_dir.as_posix(),
                "--provider",
                "openai",
                "--allow-live-smoke",
                "false",
                "--allow-network",
                "true",
                "--confirm-manual-live-smoke",
                "true",
                "--use-stdlib-openai-transport",
                "true",
            ]
        )

        self.assertEqual(exit_code, 1)
        self.assertFalse((run_dir / "model_provider_live_smoke_result.json").exists())

    def test_manual_cli_runs_only_through_existing_runner_denial_without_env(self):
        output_dir = self.make_output_dir()
        plan_path = self.build_plan(output_dir)
        run_dir = output_dir / "run"
        run_dir.mkdir()
        payload_path = run_dir / "manual_payload.json"

        payload = run_manual_model_provider_live_smoke(
            plan_path=plan_path,
            output_dir=run_dir,
            provider="openai",
            allow_live_smoke=True,
            allow_network=True,
            confirm_manual_live_smoke=True,
            use_stdlib_openai_transport=True,
            output_payload_path=payload_path,
        )

        self.assertFalse(payload["complete"])
        self.assertEqual(payload["status"], "disabled_by_environment_flag")
        self.assertFalse(payload["live_provider_called"])
        self.assertFalse(payload["network_used_by_runner"])
        self.assertFalse(payload["api_key_value_persisted"])
        self.assertFalse(payload["api_key_value_logged"])
        self.assertTrue(payload_path.exists())
        self.assertTrue((run_dir / "model_provider_live_smoke_result.json").exists())
        self.assertTrue((run_dir / "openai_explicit_transport").is_dir())
        self.assertFalse(
            (run_dir / "openai_explicit_transport" / "openai_explicit_transport_result.json").exists()
        )

    def test_cli_denial_path_writes_no_secret_values(self):
        output_dir = self.make_output_dir()
        plan_path = self.build_plan(output_dir)
        run_dir = output_dir / "run"
        run_dir.mkdir()
        payload_path = run_dir / "manual_payload.json"

        exit_code = main(
            [
                "--plan-path",
                plan_path.as_posix(),
                "--output-dir",
                run_dir.as_posix(),
                "--provider",
                "openai",
                "--allow-live-smoke",
                "true",
                "--allow-network",
                "true",
                "--confirm-manual-live-smoke",
                "true",
                "--use-stdlib-openai-transport",
                "true",
                "--output-payload-path",
                payload_path.as_posix(),
            ]
        )

        self.assertEqual(exit_code, 1)
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in run_dir.rglob("*.json")
        )
        self.assertNotIn("secret-not-persisted", combined)
        self.assertIn("disabled_by_environment_flag", combined)

    def test_refuses_existing_output_payload(self):
        output_dir = self.make_output_dir()
        plan_path = self.build_plan(output_dir)
        run_dir = output_dir / "run"
        run_dir.mkdir()
        payload_path = run_dir / "manual_payload.json"
        payload_path.write_text("{}", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "already exists"):
            run_manual_model_provider_live_smoke(
                plan_path=plan_path,
                output_dir=run_dir,
                provider="openai",
                allow_live_smoke=True,
                allow_network=True,
                confirm_manual_live_smoke=True,
                use_stdlib_openai_transport=True,
                output_payload_path=payload_path,
            )


if __name__ == "__main__":
    unittest.main()
