import unittest
from pathlib import Path


class BrowserLocalRuntimeVerificationTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_browser_runtime_chain_files_exist(self):
        for path in (
            "kernel/personal_ai/adapters/browser_local_smoke.py",
            "kernel/personal_ai/adapters/browser_controlled_local_smoke_runner.py",
            "kernel/personal_ai/adapters/browser_playwright_disabled_local_adapter.py",
            "tests/personal_ai/test_browser_controlled_local_smoke_runner.py",
            "tests/personal_ai/test_browser_playwright_disabled_local_adapter.py",
            "docs/usage/browser_controlled_local_smoke_runner.md",
            "docs/usage/browser_playwright_disabled_local_adapter.md",
            "docs/decisions/browser_controlled_local_smoke_runner_v1.md",
            "docs/decisions/browser_playwright_disabled_local_adapter_v1.md",
        ):
            self.assertTrue(Path(path).is_file(), path)

    def test_browser_controlled_runner_remains_loopback_and_default_disabled(self):
        runner = self.read(
            "kernel/personal_ai/adapters/browser_controlled_local_smoke_runner.py"
        )

        self.assertIn("allow_browser_smoke: bool = False", runner)
        self.assertIn("SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE", runner)
        self.assertIn("loopback_only", runner)
        self.assertIn("external_network_used", runner)
        self.assertIn("credential_persistence_used", runner)
        self.assertIn("login_allowed", runner)
        self.assertIn("payment_allowed", runner)
        self.assertIn("account_creation_allowed", runner)
        self.assertIn("browser_profile_access_allowed", runner)
        self.assertIn("raw_dom_persisted", runner)
        self.assertIn("screenshot_payload_persisted", runner)

    def test_playwright_disabled_adapter_remains_no_dependency_no_import(self):
        adapter = self.read(
            "kernel/personal_ai/adapters/browser_playwright_disabled_local_adapter.py"
        )
        pyproject = self.read("pyproject.toml")

        self.assertIn("allow_playwright_adapter: bool = False", adapter)
        self.assertIn("SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER", adapter)
        self.assertIn("playwright_dependency_added", adapter)
        self.assertIn("playwright_imported", adapter)
        self.assertIn("False", adapter)
        self.assertNotIn("from playwright", adapter)
        self.assertNotIn("import playwright", adapter)
        self.assertNotIn("playwright", pyproject.lower())

    def test_browser_runtime_blocks_external_network_profile_credentials_and_sensitive_flows(self):
        files = (
            "kernel/personal_ai/adapters/browser_controlled_local_smoke_runner.py",
            "kernel/personal_ai/adapters/browser_playwright_disabled_local_adapter.py",
        )
        for path in files:
            text = self.read(path)
            for marker in (
                "external_network_used",
                "credential_persistence_used",
                "login_allowed",
                "payment_allowed",
                "account_creation_allowed",
                "browser_profile",
                "raw_dom_persisted",
                "screenshot_payload_persisted",
            ):
                self.assertIn(marker, text, path)

    def test_browser_plan_builder_rejects_external_urls_and_sensitive_intents(self):
        plan_builder = self.read("kernel/personal_ai/adapters/browser_local_smoke.py")

        self.assertIn("loopback", plan_builder.lower())
        self.assertIn("forbidden intent", plan_builder.lower())
        self.assertIn("login", plan_builder.lower())
        self.assertIn("password", plan_builder.lower())
        self.assertIn("payment", plan_builder.lower())
        self.assertIn("account", plan_builder.lower())

    def test_normal_tests_do_not_launch_real_browser(self):
        controlled_test = self.read(
            "tests/personal_ai/test_browser_controlled_local_smoke_runner.py"
        )
        playwright_test = self.read(
            "tests/personal_ai/test_browser_playwright_disabled_local_adapter.py"
        )

        self.assertIn("lambda request", controlled_test)
        self.assertIn("def transport", controlled_test)
        self.assertIn("def transport", playwright_test)
        for text in (controlled_test, playwright_test):
            self.assertNotIn("sync_playwright", text)
            self.assertNotIn("async_playwright", text)
            self.assertNotIn("chromium.launch", text)
            self.assertNotIn("firefox.launch", text)
            self.assertNotIn("webkit.launch", text)

    def test_usage_and_decision_docs_record_default_disabled_posture(self):
        docs = (
            "docs/usage/browser_controlled_local_smoke_runner.md",
            "docs/usage/browser_playwright_disabled_local_adapter.md",
            "docs/decisions/browser_controlled_local_smoke_runner_v1.md",
            "docs/decisions/browser_playwright_disabled_local_adapter_v1.md",
        )
        for path in docs:
            text = self.read(path).lower()
            self.assertIn("disabled", text, path)
            self.assertIn("loopback", text, path)
            self.assertIn("no external network", text, path)
            self.assertIn("credential", text, path)
            self.assertIn("login", text, path)
            self.assertIn("payment", text, path)


if __name__ == "__main__":
    unittest.main()
