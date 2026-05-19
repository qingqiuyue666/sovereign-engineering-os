"""Tracer-bullet tests for operational closure standard."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operational_closure_standard import (
    OperationalClosureStandard,
    build_operational_closure_standard,
    render_operational_closure_standard_markdown,
)


def gates(value: bool = True) -> dict[str, bool]:
    names = (
        "engineering_foundation_closure_complete",
        "private_operator_layer_closure_complete",
        "code_audit_workbench_closure_complete",
        "operator_daily_loop_closure_complete",
        "asset_registry_closure_complete",
        "business_delivery_closure_complete",
        "macro_research_closure_complete",
        "read_only_dashboard_closure_complete",
        "system_completion_ledger_generated",
        "full_tests_green",
        "make_ci_green",
        "git_diff_check_clean",
        "git_status_clean",
        "protected_files_preserved",
        "blocked_capabilities_preserved",
        "no_fake_green_claims",
        "no_provider_execution",
        "no_production_autonomy",
        "no_financial_execution",
        "no_trading_automation",
        "no_houdini_vfx_execution_in_this_slice",
    )
    return {name: value for name in names}


def valid_material() -> dict[str, object]:
    return {
        "standard_id": "operational-closure-standard-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "closure_status": "complete",
        "closure_gates": gates(True),
        "run_001_status": "complete",
        "follow_up_packets": ["real_system_use_run_002_task_packet", "real_system_use_run_003_task_packet"],
        "blocked_capabilities": ["provider execution blocked", "trading automation blocked"],
        "remaining_gaps": [],
        "rollback_notes": ["revert closure standard"],
        "policy_version": "operational-closure-standard-v1",
        "code_version": "0.1.0",
    }


class OperationalClosureStandardTests(unittest.TestCase):
    def test_valid_closure_standard_builds_deterministic_object(self):
        standard = build_operational_closure_standard(valid_material())

        self.assertIsInstance(standard, OperationalClosureStandard)
        self.assertEqual(standard.content_hash, digest_payload(standard.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operational_closure_standard(valid_material(), observed_at="one").content_hash,
            build_operational_closure_standard(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        standard = build_operational_closure_standard(valid_material())

        self.assertEqual(
            render_operational_closure_standard_markdown(standard),
            render_operational_closure_standard_markdown(standard),
        )

    def test_invalid_closure_status_fails_closed(self):
        material = valid_material()
        material["closure_status"] = "done"

        with self.assertRaises(ValueError):
            build_operational_closure_standard(material)

    def test_missing_closure_gates_fails_closed(self):
        material = valid_material()
        del material["closure_gates"]

        with self.assertRaises(ValueError):
            build_operational_closure_standard(material)

    def test_incomplete_gate_blocks_complete(self):
        material = valid_material()
        material["closure_gates"]["make_ci_green"] = False

        with self.assertRaises(ValueError):
            build_operational_closure_standard(material)

    def test_closure_path_defined_allowed_with_follow_up_packets(self):
        material = valid_material()
        material["closure_status"] = "closure_path_defined"
        material["closure_gates"] = gates(False)

        standard = build_operational_closure_standard(material)

        self.assertEqual(standard.closure_status, "closure_path_defined")

    def test_generated_docs_exist(self):
        self.assertTrue(Path("docs/operator/generated/operational_closure_standard.md").is_file())
        self.assertTrue(Path("docs/operator/generated/operational_closure_roadmap.md").is_file())

    def test_failure_drill_plan_exists(self):
        self.assertTrue(Path("docs/operator/generated/failure_drill_plan.md").is_file())

    def test_run_002_003_task_packets_exist(self):
        self.assertTrue(Path("docs/operator/generated/real_system_use_run_002_task_packet.md").is_file())
        self.assertTrue(Path("docs/operator/generated/real_system_use_run_003_task_packet.md").is_file())

    def test_30_day_loop_plan_exists(self):
        self.assertTrue(Path("docs/operator/generated/30_day_operating_loop_plan.md").is_file())

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operational_closure_standard.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
