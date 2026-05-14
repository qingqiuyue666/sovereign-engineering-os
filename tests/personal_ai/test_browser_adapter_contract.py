import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.browser_adapter_contract import (
    BrowserFixtureActions,
    BrowserFixtureRuntimePaths,
    build_browser_fixture_capability_request,
)


class BrowserAdapterContractTests(unittest.TestCase):
    def test_browser_fixture_request_is_local_fixture_only(self):
        request = build_browser_fixture_capability_request()

        self.assertEqual(request.adapter_id, "browser_fixture_runtime")
        self.assertEqual(request.mode, AdapterMode.LOCAL_FIXTURE)
        self.assertEqual(request.risk_class, AdapterRiskClass.LOCAL_BROWSER_FIXTURE)
        self.assertTrue(request.boundary.is_runtime_safe_for_current_branch())

    def test_allowed_actions_are_fixed(self):
        self.assertEqual(
            BrowserFixtureActions.allowed(),
            (
                "open_local_fixture",
                "inspect_title",
                "inspect_links",
                "fill_allowed_field",
                "click_allowed_button",
            ),
        )
        self.assertEqual(
            BrowserFixtureRuntimePaths().action_log_file,
            "browser_action_log.json",
        )


if __name__ == "__main__":
    unittest.main()
