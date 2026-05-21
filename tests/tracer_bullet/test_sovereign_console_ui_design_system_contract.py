"""Contract checks for the Sovereign Console UI design system."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CONTRACT = Path("docs/ui/sovereign_console_ui_design_system_contract_v1.md")

PRIMARY_NAV = ("Workspace", "Runs", "Artifacts", "Reviews", "Settings")

FORBIDDEN_FIRST_LEVEL = (
    "Dashboard",
    "Job Queue",
    "HFX Factory",
    "HFX_008 Landing Chain",
    "Context Packs",
    "Human Review",
    "Failure Quarantine",
    "Artifact Store",
    "Asset Library",
    "System Health",
    "Boundaries",
)

REJECTED_PRODUCT_FRAMES = (
    "mobile app",
    "web app",
    "SaaS dashboard",
    "chatbot clone",
    "plugin marketplace",
    "raw Qt form",
    "black sci-fi concept screen",
    "cyberpunk console",
    "game HUD",
)


class SovereignConsoleUiDesignSystemContractTests(unittest.TestCase):
    def test_contract_file_exists(self) -> None:
        self.assertTrue(CONTRACT.exists())

    def test_contract_contains_exact_five_top_level_nav_entries(self) -> None:
        labels = _canonical_nav_labels(_contract_text())
        self.assertEqual(labels, PRIMARY_NAV)
        self.assertEqual(len(labels), 5)

    def test_contract_forbids_old_first_level_page_sprawl(self) -> None:
        text = _contract_text()
        self.assertIn("Forbidden first-level nav entries:", text)
        self.assertIn("Absorption rule:", text)
        for label in FORBIDDEN_FIRST_LEVEL:
            with self.subTest(label=label):
                self.assertIn(f"- {label}", text)

    def test_contract_contains_canonical_layout_diagram(self) -> None:
        text = _contract_text()
        required = (
            "macOS titlebar / compact System Pulse chips",
            "│ Sidebar      │ Workspace                     │ Inspector     │",
            "│ 200px        │ flexible                      │ 280px         │",
            "│ Workspace    │ Large Command Bar             │ No Selection  │",
            "│ Black Box · 0 warnings · Last event · Show                    │",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_contains_apple_mission_control_direction(self) -> None:
        text = _contract_text()
        self.assertIn("Sovereign Console = Apple Mission Control Workspace", text)
        self.assertIn("macOS professional desktop app", text)
        self.assertIn("Apple/Finder/Xcode/Raycast-inspired", text)
        for frame in REJECTED_PRODUCT_FRAMES:
            with self.subTest(frame=frame):
                self.assertIn(frame, text)

    def test_contract_contains_required_design_tokens(self) -> None:
        text = _contract_text()
        for token in (
            "#F5F5F7",
            "#ECECEE",
            "#FFFFFF",
            "#F2F2F7",
            "#D1D1D6",
            "#1D1D1F",
            "#6E6E73",
            "#86868B",
            "#0D0D0D",
            "#E5E5EA",
            "#8E8E93",
            "#0A84FF",
            "#30D158",
            "#FF9F0A",
            "#FF453A",
            "#00A6A6",
            "#7D5FFF",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_contract_contains_command_bar_current_mission_and_hfx_chain(self) -> None:
        text = _contract_text()
        required = (
            "Command Bar",
            "44-52px high",
            "safe/gated",
            "must not directly execute work",
            "Current Mission Card is the hero object",
            "HFX_008 Energy Shockwave",
            "final_claim_allowed",
            "Topology Audit",
            "Proof Artifact",
            "Validation",
            "Human Review",
            "Summary",
            "Claim Gate",
            "QFormLayout table dump",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_contains_inspector_black_box_and_degraded_startup_rules(self) -> None:
        text = _contract_text()
        required = (
            "Default state must not be blank",
            "Select a mission, run, artifact, or review to inspect.",
            "Policy: Local-only",
            "Black Box · 0 warnings · Show",
            "120-140px",
            "timestamp | severity | object_id | event_type | message",
            "state = Degraded",
            "no full-screen SYSTEM SYNC LOST overlay",
            "Runtime projection unavailable. Read-only workspace is active.",
            "运行时投影不可用。当前为只读工作台。",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_contains_bilingual_labels_and_execution_boundary(self) -> None:
        text = _contract_text()
        labels = (
            ("Workspace", "工作台"),
            ("Runs", "运行"),
            ("Artifacts", "产物"),
            ("Reviews", "审查"),
            ("Settings", "设置"),
            ("Command", "命令"),
            ("Current Mission", "当前任务"),
            ("Next Action", "下一步动作"),
            ("Read-only Workspace", "只读工作台"),
            ("Runtime projection unavailable", "运行时投影不可用"),
            ("Black Box", "黑匣子"),
            ("Event Stream", "事件流"),
            ("Local-only", "仅本地"),
            ("Actions Locked", "操作已锁定"),
            ("Degraded", "降级"),
            ("Lost", "丢失"),
        )
        for english, chinese in labels:
            with self.subTest(label=english):
                self.assertIn(english, text)
                self.assertIn(chinese, text)

        boundary_phrases = (
            "GUI remains read-model + gated intent issuer only",
            "directly run subprocess",
            "directly launch Houdini",
            "directly call ComfyUI",
            "directly call DaVinci",
            "directly create network clients",
            "directly mutate SQLite job queue",
            "directly mutate artifact store",
            "delete/overwrite files",
            "upload files",
            "bypass OS Runtime",
            "bypass Job Queue",
            "bypass Human Review Gate",
            "claim final completion",
            "GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry",
        )
        for phrase in boundary_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _canonical_nav_labels(text: str) -> tuple[str, ...]:
    match = re.search(
        r"CANONICAL_PRIMARY_NAVIGATION:\n(?P<nav>(?:\d+\. .+\n){5})",
        text,
    )
    if match is None:
        raise AssertionError("CANONICAL_PRIMARY_NAVIGATION block missing")
    return tuple(line.split(". ", 1)[1] for line in match.group("nav").splitlines())


if __name__ == "__main__":
    unittest.main()
