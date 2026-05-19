"""Tracer-bullet tests for operator daily loop reports."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_daily_loop import (
    OperatorDailyLoop,
    build_operator_daily_loop,
    render_operator_daily_loop_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "loop_id": "operator-daily-loop-test",
        "date_label": "2026-05-19",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "current_phase": "non-Houdini closure",
        "today_focus": ["finish reports"],
        "completed_recently": ["runtime contracts"],
        "active_constraints": ["no provider calls"],
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "current_risks": ["verification could fail"],
        "next_actions": ["run tests"],
        "stop_conditions": ["failed gate"],
        "verification_required": ["make ci"],
        "rollback_notes": ["revert loop docs"],
        "policy_version": "operator-daily-loop-v1",
        "code_version": "0.1.0",
    }


class OperatorDailyLoopTests(unittest.TestCase):
    def test_valid_loop_builds_deterministic_object(self):
        loop = build_operator_daily_loop(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(loop, OperatorDailyLoop)
        self.assertEqual(loop.content_hash, digest_payload(loop.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_daily_loop(valid_material(), observed_at="one").content_hash,
            build_operator_daily_loop(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        loop = build_operator_daily_loop(valid_material())

        self.assertEqual(render_operator_daily_loop_markdown(loop), render_operator_daily_loop_markdown(loop))

    def test_missing_next_actions_fails_closed(self):
        material = valid_material()
        del material["next_actions"]

        with self.assertRaises(ValueError):
            build_operator_daily_loop(material)

    def test_missing_stop_conditions_fails_closed(self):
        material = valid_material()
        del material["stop_conditions"]

        with self.assertRaises(ValueError):
            build_operator_daily_loop(material)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_daily_loop.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
