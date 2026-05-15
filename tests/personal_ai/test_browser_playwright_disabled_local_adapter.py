import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_local_smoke import build_browser_local_smoke_plan
from kernel.personal_ai.adapters.browser_playwright_disabled_local_adapter import (
    run_browser_playwright_disabled_local_adapter,
)


class BrowserPlaywrightDisabledLocalAdapterTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_actions(self, output_dir: Path, actions=None) -> Path:
        actions_path = output_dir / "actions.json"
        actions_path.write_text(
            json.dumps(
                {
                    "actions": actions
                    if actions is not None
                    else [{"action": "open", "selector": "body"}]
                }
            ),
            encoding="utf-8",
        )
        return actions_path

    def build_plan(self, root: Path, target_url="http://127.0.0.1:8080") -> Path:
        result = build_browser_local_smoke_plan(
            self.write_actions(root),
            root,
            target_url=target_url,
        )
        return result.plan_path

    def test_denies_by_default_without_playwright_import_or_transport(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        run_dir = root / "run"
        run_dir.mkdir()

        result = run_browser_playwright_disabled_local_adapter(plan_path, run_dir)

        self.assertEqual(result.status, "disabled_by_callsite")
        self.assertFalse(result.playwright_imported)
        self.assertFalse(result.real_browser_launched)
        self.assertFalse(result.external_network_used)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["playwright_dependency_added"])
        self.assertFalse(payload["playwright_imported"])
        self.assertFalse(payload["playwright_transport_called"])
        self.assertFalse(payload["real_browser_launched"])

    def test_denies_without_environment_flag(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        run_dir = root / "run"
        run_dir.mkdir()

        result = run_browser_playwright_disabled_local_adapter(
            plan_path,
            run_dir,
            allow_playwright_adapter=True,
            playwright_transport=lambda request: {"status": "ok"},
        )

        self.assertEqual(result.status, "disabled_by_environment_flag")
        self.assertFalse(result.real_browser_launched)

    def test_denies_without_explicit_transport(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        run_dir = root / "run"
        run_dir.mkdir()

        result = run_browser_playwright_disabled_local_adapter(
            plan_path,
            run_dir,
            environ={"SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER": "true"},
            allow_playwright_adapter=True,
        )

        self.assertEqual(result.status, "missing_explicit_playwright_transport")
        self.assertFalse(result.real_browser_launched)

    def test_allows_injected_playwright_like_transport_after_all_gates(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        run_dir = root / "run"
        run_dir.mkdir()
        calls = []

        def transport(request):
            calls.append(request)
            self.assertTrue(request["loopback_only"])
            self.assertFalse(request["external_network_allowed"])
            self.assertFalse(request["real_user_profile_allowed"])
            self.assertFalse(request["persistent_context_allowed"])
            self.assertFalse(request["credential_persistence_allowed"])
            self.assertFalse(request["login_allowed"])
            self.assertFalse(request["payment_allowed"])
            self.assertFalse(request["account_creation_allowed"])
            return {
                "status": "ok",
                "external_network_used": False,
                "credential_persistence_used": False,
                "login_performed": False,
                "payment_performed": False,
                "account_creation_performed": False,
                "browser_profile_used": False,
                "raw_dom_persisted": False,
                "screenshot_payload_persisted": False,
            }

        result = run_browser_playwright_disabled_local_adapter(
            plan_path,
            run_dir,
            environ={"SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER": "true"},
            allow_playwright_adapter=True,
            playwright_transport=transport,
        )

        self.assertEqual(
            result.status,
            "completed_via_explicit_playwright_like_transport",
        )
        self.assertFalse(result.playwright_imported)
        self.assertTrue(result.real_browser_launched)
        self.assertFalse(result.external_network_used)
        self.assertFalse(result.browser_profile_used)
        self.assertEqual(len(calls), 1)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["playwright_dependency_added"])
        self.assertFalse(payload["playwright_imported"])
        self.assertTrue(payload["playwright_transport_called"])
        self.assertFalse(payload["external_network_used"])
        self.assertTrue(payload["controlled_runner_validation_complete"])

    def test_unsafe_transport_response_is_contained_by_controlled_runner_validation(self):
        root = self.make_output_dir()
        plan_path = self.build_plan(root)
        run_dir = root / "run"
        run_dir.mkdir()

        result = run_browser_playwright_disabled_local_adapter(
            plan_path,
            run_dir,
            environ={"SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER": "true"},
            allow_playwright_adapter=True,
            playwright_transport=lambda request: {
                "status": "ok",
                "external_network_used": True,
            },
        )

        self.assertEqual(
            result.status,
            "completed_via_explicit_playwright_like_transport",
        )
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["controlled_runner_validation_complete"])
        runner_payload = json.loads(
            (run_dir / "controlled_local_smoke_runner" / "browser_controlled_local_smoke_result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(
            "external_network_used",
            runner_payload["transport_response_validation"]["failures"],
        )

    def test_external_url_and_sensitive_intent_rejected_by_plan_builder(self):
        external_root = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "loopback"):
            build_browser_local_smoke_plan(
                self.write_actions(external_root),
                external_root,
                target_url="https://example.com",
            )

        sensitive_root = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "forbidden intent"):
            build_browser_local_smoke_plan(
                self.write_actions(
                    sensitive_root,
                    actions=[{"action": "open", "text": "signup password"}],
                ),
                sensitive_root,
                target_url="http://localhost:8080",
            )

    def test_malformed_plan_fails_closed(self):
        root = self.make_output_dir()
        bad_plan = root / "bad_plan.json"
        bad_plan.write_text("{bad", encoding="utf-8")
        run_dir = root / "run"
        run_dir.mkdir()

        result = run_browser_playwright_disabled_local_adapter(
            bad_plan,
            run_dir,
            environ={"SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER": "true"},
            allow_playwright_adapter=True,
        )

        self.assertEqual(result.status, "failed_closed")
        self.assertFalse(result.playwright_imported)
        self.assertFalse(result.real_browser_launched)
        self.assertIsNotNone(result.failure_path)


if __name__ == "__main__":
    unittest.main()
