"""Tracer-bullet tests for system completion ledger."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.system_completion_ledger import (
    SystemCompletionLedger,
    build_system_completion_ledger,
    render_system_completion_ledger_markdown,
)


def valid_material() -> dict[str, object]:
    modules = [
        {"module": "Engineering foundation", "closure_state": "complete"},
        {"module": "Private operator layer", "closure_state": "complete"},
        {"module": "Code Audit Workbench", "closure_state": "complete"},
        {"module": "Operator Daily Loop", "closure_state": "complete"},
        {"module": "Asset Registry operationalization", "closure_state": "complete"},
        {"module": "Business Delivery operationalization", "closure_state": "complete"},
        {"module": "Macro Research", "closure_state": "complete"},
        {"module": "Read-only dashboard", "closure_state": "complete"},
    ]
    return {
        "ledger_id": "system-completion-ledger-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "excluded_lines": ["Houdini/VFX execution line remains excluded"],
        "modules": modules,
        "previous_estimates": [
            "Engineering foundation: ~90%",
            "Private operator layer: ~85%",
            "Code Audit Workbench: ~75-80%",
            "Operator Daily Loop: ~45-55%",
            "Asset Registry operationalization: ~40-50%",
            "Business Delivery operationalization: ~25-35%",
            "Macro Research: ~35-45%",
            "Overall system landing excluding Houdini: ~70-78%",
        ],
        "target_estimates": [
            "Engineering foundation: 100%",
            "Private operator layer: 100%",
            "Code Audit Workbench: 100%",
            "Operator Daily Loop: 100%",
            "Asset Registry operationalization: 100%",
            "Business Delivery operationalization: 100%",
            "Macro Research: 100%",
            "Overall non-Houdini system closure: 100%",
        ],
        "achieved_status": {"overall": "complete"},
        "closure_gates": {"all_modules_complete": True},
        "open_gaps": [],
        "closed_gaps": ["non-Houdini modules closed"],
        "next_required_runs": ["real system use run 002"],
        "blocked_capabilities": ["provider execution blocked", "trading automation blocked"],
        "completion_decision": "complete",
        "policy_version": "system-completion-ledger-v1",
        "code_version": "0.1.0",
    }


class SystemCompletionLedgerTests(unittest.TestCase):
    def test_valid_ledger_builds_deterministic_object(self):
        ledger = build_system_completion_ledger(valid_material())

        self.assertIsInstance(ledger, SystemCompletionLedger)
        self.assertEqual(ledger.content_hash, digest_payload(ledger.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_system_completion_ledger(valid_material(), observed_at="one").content_hash,
            build_system_completion_ledger(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        ledger = build_system_completion_ledger(valid_material())

        self.assertEqual(render_system_completion_ledger_markdown(ledger), render_system_completion_ledger_markdown(ledger))

    def test_missing_previous_estimates_fails_closed(self):
        material = valid_material()
        del material["previous_estimates"]

        with self.assertRaises(ValueError):
            build_system_completion_ledger(material)

    def test_missing_target_estimates_fails_closed(self):
        material = valid_material()
        del material["target_estimates"]

        with self.assertRaises(ValueError):
            build_system_completion_ledger(material)

    def test_missing_excluded_lines_fails_closed(self):
        material = valid_material()
        del material["excluded_lines"]

        with self.assertRaises(ValueError):
            build_system_completion_ledger(material)

    def test_incomplete_module_blocks_complete(self):
        material = valid_material()
        material["modules"][0]["closure_state"] = "in_progress"

        with self.assertRaises(ValueError):
            build_system_completion_ledger(material)

    def test_generated_ledger_exists(self):
        self.assertTrue(Path("docs/operator/generated/system_completion_ledger.md").is_file())

    def test_ledger_excludes_houdini_vfx_execution_line(self):
        text = Path("docs/operator/generated/system_completion_ledger.md").read_text(encoding="utf-8").lower()

        self.assertIn("houdini/vfx execution line remains excluded", text)

    def test_ledger_includes_previous_and_target_estimates(self):
        text = Path("docs/operator/generated/system_completion_ledger.md").read_text(encoding="utf-8")

        self.assertIn("Engineering foundation: ~90%", text)
        self.assertIn("Engineering foundation: 100%", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/system_completion_ledger.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
