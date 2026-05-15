import unittest
from pathlib import Path


class MainRuntimeLiveSmokeVerificationTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_manual_live_smoke_cli_surface_exists(self):
        cli = self.read("kernel/personal_ai/model_provider_manual_live_smoke_cli.py")

        self.assertIn("run_manual_model_provider_live_smoke", cli)
        self.assertIn("--allow-live-smoke", cli)
        self.assertIn("--allow-network", cli)
        self.assertIn("--confirm-manual-live-smoke", cli)
        self.assertIn("--use-stdlib-openai-transport", cli)
        self.assertIn("_parse_exact_true", cli)
        self.assertIn("SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE", self.read("kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py"))
        self.assertIn("SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT", self.read("kernel/personal_ai/adapters/openai_explicit_transport.py"))

    def test_model_provider_live_smoke_chain_files_exist(self):
        required_paths = (
            "kernel/personal_ai/adapters/model_provider_activation_package.py",
            "kernel/personal_ai/adapters/model_provider_live_smoke.py",
            "kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py",
            "kernel/personal_ai/adapters/model_provider_transport_adapter.py",
            "kernel/personal_ai/adapters/openai_explicit_transport.py",
            "kernel/personal_ai/model_provider_manual_live_smoke_cli.py",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_live_smoke_defaults_remain_disabled(self):
        runner = self.read("kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py")
        openai_transport = self.read("kernel/personal_ai/adapters/openai_explicit_transport.py")
        manual_cli = self.read("kernel/personal_ai/model_provider_manual_live_smoke_cli.py")

        self.assertIn("allow_live_smoke: bool = False", runner)
        self.assertIn("allow_network: bool = False", openai_transport)
        self.assertIn("enabled_by_default", openai_transport)
        self.assertIn("False", openai_transport)
        self.assertIn("use_stdlib_openai_transport", manual_cli)
        self.assertIn("must be exactly true", manual_cli)

    def test_normal_tests_cover_live_smoke_without_hitting_provider(self):
        test_paths = (
            "tests/personal_ai/test_model_provider_disabled_live_smoke_runner.py",
            "tests/personal_ai/test_model_provider_explicit_transport_suite.py",
            "tests/personal_ai/test_model_provider_manual_live_smoke_cli.py",
        )
        for path in test_paths:
            text = self.read(path)
            self.assertIn("secret-not-persisted", text)
            self.assertIn("assertNotIn", text)

        explicit_suite = self.read("tests/personal_ai/test_model_provider_explicit_transport_suite.py")
        self.assertIn("lambda payload, key", explicit_suite)
        self.assertIn("http_transport", explicit_suite)
        self.assertNotIn("stdlib_openai_responses_transport(", explicit_suite)

    def test_no_secret_or_raw_response_persistence_posture(self):
        files = (
            "kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py",
            "kernel/personal_ai/adapters/openai_explicit_transport.py",
            "kernel/personal_ai/model_provider_manual_live_smoke_cli.py",
        )
        for path in files:
            text = self.read(path)
            self.assertIn("api_key_value_persisted", text)
            self.assertIn("api_key_value_logged", text)
            self.assertIn("False", text)
            self.assertIn("tool_calls_allowed", text)
            self.assertIn("file_edits_allowed", text)

        openai_transport = self.read("kernel/personal_ai/adapters/openai_explicit_transport.py")
        self.assertIn("raw_provider_response_persisted", openai_transport)
        self.assertIn("False", openai_transport)

    def test_usage_and_decision_docs_exist(self):
        required_docs = (
            "docs/usage/model_provider_manual_live_smoke_cli.md",
            "docs/decisions/model_provider_manual_live_smoke_cli_v1.md",
            "docs/decisions/model_provider_explicit_transport_suite_v1.md",
            "docs/decisions/model_provider_disabled_live_smoke_runner_v1.md",
            "docs/decisions/model_provider_controlled_activation_v1.md",
        )
        for path in required_docs:
            text = self.read(path)
            self.assertIn("OpenAI", text)
            self.assertIn("default", text.lower())


if __name__ == "__main__":
    unittest.main()
