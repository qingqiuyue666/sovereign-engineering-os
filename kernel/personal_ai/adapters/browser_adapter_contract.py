"""Contract helpers for the local fixture browser adapter."""

from dataclasses import dataclass

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRiskClass,
)

__all__ = [
    "BrowserFixtureActions",
    "BrowserFixtureRuntimePaths",
    "build_browser_fixture_capability_request",
]


class BrowserFixtureActions:
    OPEN_LOCAL_FIXTURE = "open_local_fixture"
    INSPECT_TITLE = "inspect_title"
    INSPECT_LINKS = "inspect_links"
    FILL_ALLOWED_FIELD = "fill_allowed_field"
    CLICK_ALLOWED_BUTTON = "click_allowed_button"

    @classmethod
    def allowed(cls) -> tuple[str, ...]:
        return (
            cls.OPEN_LOCAL_FIXTURE,
            cls.INSPECT_TITLE,
            cls.INSPECT_LINKS,
            cls.FILL_ALLOWED_FIELD,
            cls.CLICK_ALLOWED_BUTTON,
        )


@dataclass(frozen=True)
class BrowserFixtureRuntimePaths:
    action_log_file: str = "browser_action_log.json"
    evidence_manifest_file: str = "browser_evidence_manifest.json"


def build_browser_fixture_capability_request() -> AdapterCapabilityRequest:
    return AdapterCapabilityRequest(
        adapter_id="browser_fixture_runtime",
        capability="open_local_fixture",
        mode=AdapterMode.LOCAL_FIXTURE,
        risk_class=AdapterRiskClass.LOCAL_BROWSER_FIXTURE,
        requested_operations=("parse_local_html_fixture", "write_evidence_log"),
        boundary=AdapterExecutionBoundary(),
    )
