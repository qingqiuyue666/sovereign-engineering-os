import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_fixture_runtime import (
    run_browser_fixture,
    run_browser_fixture_from_actions_file,
)
from kernel.personal_ai.io_utils import write_json_atomically


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BrowserFixtureRuntimeTests(unittest.TestCase):
    def build_workspace(self, html=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        fixture_dir = root / "fixture"
        output_dir = root / "output"
        fixture_dir.mkdir()
        output_dir.mkdir()
        fixture_path = fixture_dir / "page.html"
        fixture_path.write_text(
            html
            or """
<!doctype html>
<html>
  <head><title>Local Fixture</title></head>
  <body>
    <a href="/local">Local link</a>
    <form>
      <input name="query" data-seos-allowed-field="true" />
      <button id="go" type="submit" data-seos-allowed-button="true" data-seos-allow-submit="true">Go</button>
    </form>
  </body>
</html>
""",
            encoding="utf-8",
        )
        return root, fixture_path, output_dir

    def test_runs_allowed_local_fixture_actions_and_writes_evidence(self):
        _, fixture_path, output_dir = self.build_workspace()

        result = run_browser_fixture(
            fixture_path,
            output_dir,
            [
                {"action": "open_local_fixture"},
                {"action": "inspect_title"},
                {"action": "inspect_links"},
                {
                    "action": "fill_allowed_field",
                    "field_name": "query",
                    "value": "RAW_TYPED_VALUE",
                },
                {"action": "click_allowed_button", "button_id": "go"},
            ],
            allow_form_submit=True,
        )
        action_log = read_json(result.action_log_path)
        evidence = read_json(result.evidence_manifest_path)

        self.assertEqual(result.action_count, 5)
        self.assertFalse(action_log["external_network_used"])
        self.assertFalse(action_log["real_browser_runtime_used"])
        self.assertFalse(action_log["playwright_runtime_used"])
        self.assertTrue(action_log["external_navigation_denied_by_default"])
        self.assertFalse(action_log["credential_storage_used"])
        self.assertEqual(evidence["before_dom_snapshot"]["title"], "Local Fixture")
        self.assertEqual(evidence["after_dom_snapshot"]["filled_fields"]["query"]["value_length"], 15)
        self.assertEqual(evidence["screenshot_evidence"]["mode"], "dom_metadata_only_fixture")
        self.assertFalse(evidence["real_screenshot_captured"])
        self.assertTrue(evidence["timeout_quarantine_policy"]["failure_quarantine_required"])
        self.assertNotIn(
            "RAW_TYPED_VALUE",
            result.action_log_path.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "RAW_TYPED_VALUE",
            result.evidence_manifest_path.read_text(encoding="utf-8"),
        )

    def test_rejects_external_fixture_url_and_action_url(self):
        _, fixture_path, output_dir = self.build_workspace()

        with self.assertRaises(ValueError):
            run_browser_fixture("https://example.com", output_dir, [])
        with self.assertRaises(ValueError):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "open_local_fixture", "url": "https://example.com"}],
            )

    def test_rejects_external_fixture_link_unless_domain_allowlisted(self):
        _, fixture_path, output_dir = self.build_workspace(
            """
<html><head><title>Fixture</title></head><body>
<a href="https://example.test/page">External</a>
</body></html>
"""
        )

        with self.assertRaisesRegex(ValueError, "domain allowlist"):
            run_browser_fixture(fixture_path, output_dir, [{"action": "inspect_links"}])

        result = run_browser_fixture(
            fixture_path,
            output_dir,
            [{"action": "inspect_links"}],
            allowed_domains=("example.test",),
        )
        evidence = read_json(result.evidence_manifest_path)

        self.assertEqual(evidence["domain_allowlist"], ["example.test"])

    def test_rejects_unallowed_actions(self):
        _, fixture_path, output_dir = self.build_workspace()

        with self.assertRaises(ValueError):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "submit_payment"}],
            )

    def test_rejects_credential_field(self):
        _, fixture_path, output_dir = self.build_workspace(
            """
<html><head><title>Fixture</title></head><body>
<input name="password" type="password" data-seos-allowed-field="true" />
</body></html>
"""
        )

        with self.assertRaises(ValueError):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [
                    {
                        "action": "fill_allowed_field",
                        "field_name": "password",
                        "value": "dummy",
                    }
                ],
            )

    def test_rejects_payment_and_account_creation_actions(self):
        _, fixture_path, output_dir = self.build_workspace(
            """
<html><head><title>Fixture</title></head><body>
<button id="checkout" data-seos-allowed-button="true">Pay</button>
<input name="api_key" data-seos-allowed-field="true" />
</body></html>
"""
        )

        with self.assertRaisesRegex(ValueError, "sensitive browser action"):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "click_allowed_button", "button_id": "checkout"}],
            )
        with self.assertRaisesRegex(ValueError, "sensitive browser action"):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [
                    {
                        "action": "fill_allowed_field",
                        "field_name": "api_key",
                        "value": "dummy",
                    }
                ],
            )

    def test_rejects_form_submission_without_explicit_fixture_policy(self):
        _, fixture_path, output_dir = self.build_workspace(
            """
<html><head><title>Fixture</title></head><body>
<button id="go" type="submit" data-seos-allowed-button="true">Go</button>
</body></html>
"""
        )

        with self.assertRaises(ValueError):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "click_allowed_button", "button_id": "go"}],
            )

    def test_rejects_submit_without_explicit_approval_gate_even_when_fixture_allows_it(self):
        _, fixture_path, output_dir = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "explicit approval gate"):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "click_allowed_button", "button_id": "go"}],
            )

    def test_rejects_timeout_policy_outside_fixture_bounds(self):
        _, fixture_path, output_dir = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "timeout_seconds exceeds"):
            run_browser_fixture(
                fixture_path,
                output_dir,
                [{"action": "open_local_fixture"}],
                timeout_seconds=31,
            )

    def test_refuses_output_overwrite_and_fixture_directory_output(self):
        _, fixture_path, output_dir = self.build_workspace()
        (output_dir / "browser_action_log.json").write_text("{}", encoding="utf-8")

        with self.assertRaises(ValueError):
            run_browser_fixture(fixture_path, output_dir, [])

        unsafe_output = fixture_path.parent / "generated"
        unsafe_output.mkdir()
        with self.assertRaises(ValueError):
            run_browser_fixture(fixture_path, unsafe_output, [])

    def test_runs_from_actions_file(self):
        root, fixture_path, output_dir = self.build_workspace()
        actions_path = root / "actions.json"
        write_json_atomically(
            actions_path,
            {
                "policy": {"timeout_seconds": 3},
                "actions": [{"action": "open_local_fixture"}],
            },
        )
        bad_actions_path = root / "bad_actions.json"
        bad_actions_path.write_text("{bad", encoding="utf-8")

        result = run_browser_fixture_from_actions_file(
            fixture_path,
            actions_path,
            output_dir,
        )
        self.assertEqual(result.action_count, 1)
        with self.assertRaises(ValueError):
            run_browser_fixture_from_actions_file(
                fixture_path,
                bad_actions_path,
                output_dir,
            )


if __name__ == "__main__":
    unittest.main()
