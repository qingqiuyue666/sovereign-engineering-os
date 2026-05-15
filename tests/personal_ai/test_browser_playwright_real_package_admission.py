import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_playwright_real_package_admission import (
    build_browser_playwright_real_package_admission,
    verify_browser_playwright_real_package_admission,
)


class BrowserPlaywrightRealPackageAdmissionTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_builds_candidate_admission_without_installing_or_importing_playwright(self):
        output_dir = self.make_output_dir()

        result = build_browser_playwright_real_package_admission(output_dir)

        self.assertTrue(result.complete)
        self.assertEqual(result.package_name, "playwright")
        self.assertFalse(result.admitted)
        self.assertFalse(result.dependency_added)
        self.assertFalse(result.playwright_imported)
        self.assertFalse(result.browser_launched)
        admission = json.loads(result.admission_path.read_text(encoding="utf-8"))
        self.assertEqual(admission["admission_status"], "candidate_only_not_installed")
        self.assertFalse(admission["admitted_for_installation"])
        self.assertFalse(admission["dependency_added"])
        self.assertFalse(admission["playwright_imported"])
        self.assertFalse(admission["browser_launched"])
        self.assertTrue(admission["loopback_only"])
        self.assertTrue(admission["isolated_temp_profile_required"])

    def test_admission_forbids_external_network_profile_credentials_and_sensitive_flows(self):
        output_dir = self.make_output_dir()
        result = build_browser_playwright_real_package_admission(output_dir)
        admission = json.loads(result.admission_path.read_text(encoding="utf-8"))

        for field_name in (
            "external_network_allowed",
            "external_network_used",
            "real_user_profile_allowed",
            "persistent_context_allowed",
            "credential_persistence_allowed",
            "login_allowed",
            "signup_allowed",
            "account_creation_allowed",
            "payment_allowed",
            "raw_dom_persistence_allowed",
            "screenshot_payload_persistence_allowed_by_default",
        ):
            self.assertFalse(admission[field_name], field_name)

    def test_verification_rejects_tampered_admission(self):
        output_dir = self.make_output_dir()
        result = build_browser_playwright_real_package_admission(output_dir)
        admission = json.loads(result.admission_path.read_text(encoding="utf-8"))
        admission["external_network_allowed"] = True
        tampered_path = output_dir / "tampered_admission.json"
        tampered_path.write_text(json.dumps(admission), encoding="utf-8")

        verification = verify_browser_playwright_real_package_admission(
            tampered_path,
            output_dir / "tampered_verification.json",
        )

        self.assertFalse(verification["complete"])
        self.assertIn("external_network_allowed_must_be_false", verification["failures"])

    def test_rejects_non_loopback_or_profile_or_network_policy(self):
        output_dir = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "package_name"):
            build_browser_playwright_real_package_admission(
                output_dir,
                package_name="selenium",
            )
        with self.assertRaisesRegex(ValueError, "target_url_policy"):
            build_browser_playwright_real_package_admission(
                self.make_output_dir(),
                target_url_policy="external_allowed",
            )
        with self.assertRaisesRegex(ValueError, "profile_policy"):
            build_browser_playwright_real_package_admission(
                self.make_output_dir(),
                profile_policy="real_user_profile_allowed",
            )
        with self.assertRaisesRegex(ValueError, "network_policy"):
            build_browser_playwright_real_package_admission(
                self.make_output_dir(),
                network_policy="external_network_allowed",
            )

    def test_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        build_browser_playwright_real_package_admission(output_dir)
        with self.assertRaisesRegex(ValueError, "already exists"):
            build_browser_playwright_real_package_admission(output_dir)

    def test_module_does_not_import_playwright_or_launch_browser(self):
        module_text = Path(
            "kernel/personal_ai/adapters/browser_playwright_real_package_admission.py"
        ).read_text(encoding="utf-8")
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertNotIn("from playwright", module_text)
        self.assertNotIn("import playwright", module_text)
        self.assertNotIn("sync_playwright", module_text)
        self.assertNotIn("async_playwright", module_text)
        self.assertNotIn("chromium.launch", module_text)
        self.assertNotIn("firefox.launch", module_text)
        self.assertNotIn("webkit.launch", module_text)
        self.assertNotIn("playwright", pyproject.lower())


if __name__ == "__main__":
    unittest.main()
