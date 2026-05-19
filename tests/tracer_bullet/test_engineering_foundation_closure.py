"""Tracer-bullet tests for engineering foundation closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.engineering_foundation_closure import (
    EngineeringFoundationClosure,
    build_engineering_foundation_closure,
    render_engineering_foundation_closure_markdown,
)


def valid_material() -> dict[str, object]:
    gates = {
        "tracer_bullet_green": True,
        "schemas_green": True,
        "acceptance_green": True,
        "make_ci_green": True,
        "git_diff_check_clean": True,
        "git_status_clean": True,
        "root_integrity_preserved": True,
        "makefile_unchanged_unless_authorized": True,
        "root_readme_unchanged_unless_authorized": True,
        "health_gate_wiring_unchanged_unless_authorized": True,
        "blocked_capabilities_preserved": True,
        "no_provider_execution": True,
        "no_production_autonomy": True,
        "no_financial_execution": True,
        "no_trading_automation": True,
        "no_houdini_vfx_execution_in_this_slice": True,
    }
    return {
        "closure_id": "foundation-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "branch": "codex-nonhoudini-system-completion-v1",
        "foundation_gates": gates,
        "verification_matrix": {"tests": "caller verified"},
        "protected_file_status": {"Makefile": "preserved"},
        "root_integrity_status": {"status": "preserved"},
        "ci_status": {"make_ci": "caller verified"},
        "blocked_capability_status": {"status": "preserved"},
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert closure commit"],
        "policy_version": "engineering-foundation-closure-v1",
        "code_version": "0.1.0",
    }


class EngineeringFoundationClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_engineering_foundation_closure(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(closure, EngineeringFoundationClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        first = build_engineering_foundation_closure(valid_material(), observed_at="one")
        second = build_engineering_foundation_closure(valid_material(), observed_at="two")

        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_deterministic(self):
        closure = build_engineering_foundation_closure(valid_material())

        self.assertEqual(
            render_engineering_foundation_closure_markdown(closure),
            render_engineering_foundation_closure_markdown(closure),
        )

    def test_missing_closure_id_fails_closed(self):
        material = valid_material()
        del material["closure_id"]

        with self.assertRaises(ValueError):
            build_engineering_foundation_closure(material)

    def test_missing_verification_matrix_fails_closed(self):
        material = valid_material()
        del material["verification_matrix"]

        with self.assertRaises(ValueError):
            build_engineering_foundation_closure(material)

    def test_incomplete_gate_blocks_complete(self):
        material = valid_material()
        material["foundation_gates"]["make_ci_green"] = False

        with self.assertRaises(ValueError):
            build_engineering_foundation_closure(material)

    def test_blocked_capability_violation_blocks_complete(self):
        material = valid_material()
        material["blocked_capability_status"]["violation"] = "provider boundary changed"

        with self.assertRaises(ValueError):
            build_engineering_foundation_closure(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_provider_response", "env", "secret", "token"):
            material = valid_material()
            material["verification_matrix"][field_name] = "blocked"
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    build_engineering_foundation_closure(material)

    def test_generated_closure_doc_exists(self):
        self.assertTrue(Path("docs/operator/generated/engineering_foundation_closure.md").is_file())

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/engineering_foundation_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
