"""Skill contract checks for future Sovereign Console UI work."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path("docs/ui/sovereign_console_ui_skill_v1.md")
CONTRACT = Path("docs/ui/sovereign_console_ui_design_system_contract_v1.md")
ENGINEERING_SPEC = Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md")

PRIMARY_NAV = ("Workspace", "Runs", "Artifacts", "Reviews", "Settings")


class SovereignConsoleUiSkillContractTests(unittest.TestCase):
    def test_skill_file_exists_and_points_to_binding_contract(self) -> None:
        self.assertTrue(SKILL.exists())
        self.assertTrue(CONTRACT.exists())
        text = _skill_text()
        self.assertIn("Use this repository-local skill", text)
        self.assertIn(str(CONTRACT), text)
        self.assertIn("Sovereign Console = Apple Mission Control Workspace", text)

    def test_engineering_spec_integrates_skill_and_contract(self) -> None:
        text = ENGINEERING_SPEC.read_text(encoding="utf-8")
        self.assertIn(str(CONTRACT), text)
        self.assertIn(str(SKILL), text)
        self.assertIn("design system contract", text)

    def test_skill_repeats_exact_primary_navigation(self) -> None:
        labels = _primary_nav_labels(_skill_text())
        self.assertEqual(labels, PRIMARY_NAV)
        self.assertEqual(len(labels), 5)

    def test_skill_preserves_layout_visual_and_component_contracts(self) -> None:
        text = _skill_text()
        required = (
            "200px sidebar",
            "flexible workspace",
            "280px",
            "compact top System Pulse",
            "collapsed bottom Black Box",
            "#F5F5F7",
            "#ECECEE",
            "#FFFFFF",
            "#0D0D0D",
            "#0A84FF",
            "large Raycast/Codex-style Command Bar",
            "Current Mission Card",
            "HFX_008 Energy Chain",
            "final_claim_allowed",
            "Black Box · 0 warnings · Show",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_skill_preserves_hfx_chain_degraded_rule_and_i18n(self) -> None:
        text = _skill_text()
        required = (
            "Topology Audit",
            "Proof Artifact",
            "Validation",
            "Human Review",
            "Summary",
            "Claim Gate",
            "Startup without runtime projection is Degraded, not Lost",
            "Runtime projection unavailable. Read-only workspace is active.",
            "运行时投影不可用。当前为只读工作台。",
            "Workspace / 工作台",
            "Runs / 运行",
            "Artifacts / 产物",
            "Reviews / 审查",
            "Settings / 设置",
            "Command / 命令",
            "Current Mission / 当前任务",
            "Next Action / 下一步动作",
            "Local-only / 仅本地",
            "Actions Locked / 操作已锁定",
            "Degraded / 降级",
            "Lost / 丢失",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_skill_rejects_wrong_product_frames_and_execution_boundary_breaks(self) -> None:
        text = _skill_text()
        required = (
            "mobile app",
            "web app",
            "SaaS dashboard",
            "chatbot clone",
            "plugin marketplace",
            "raw Qt form",
            "black sci-fi concept screen",
            "cyberpunk console",
            "game HUD",
            "raw QFormLayout mission dumps",
            "raw QPushButton navigation stacks",
            "QGraphicsView node editors",
            "read-model + gated intent issuer only",
            "directly run subprocesses",
            "launch Houdini",
            "call ComfyUI",
            "call DaVinci",
            "create network clients",
            "mutate SQLite job state",
            "mutate artifact storage",
            "GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _primary_nav_labels(text: str) -> tuple[str, ...]:
    match = re.search(
        r"Only these first-level entries are allowed:\n\n(?P<nav>(?:\d+\. .+\n){5})",
        text,
    )
    if match is None:
        raise AssertionError("primary navigation block missing")
    return tuple(line.split(". ", 1)[1] for line in match.group("nav").splitlines())


if __name__ == "__main__":
    unittest.main()
