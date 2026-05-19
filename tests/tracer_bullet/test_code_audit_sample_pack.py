"""Tracer-bullet tests for the generated code audit sample pack."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import json
import unittest

from kernel.runtime.ai_worker_result_review_packet import (
    build_ai_worker_result_review_packet,
    render_ai_worker_result_review_packet_markdown,
)
from kernel.runtime.branch_audit_report import build_branch_audit_report, render_branch_audit_report_markdown
from kernel.runtime.code_audit_daily_report import (
    build_code_audit_daily_report,
    render_code_audit_daily_report_markdown,
)
from kernel.runtime.code_audit_operational_loop import (
    build_code_audit_operational_loop,
    render_code_audit_operational_loop_markdown,
)
from kernel.runtime.merge_readiness_report import (
    build_merge_readiness_report,
    render_merge_readiness_report_markdown,
)
from kernel.runtime.post_merge_retrospective_report import (
    build_post_merge_retrospective_report,
    render_post_merge_retrospective_report_markdown,
)
from tools.generate_code_audit_sample_pack import OBSERVED_AT, OUTPUT_DIR, build_outputs


SPEC_BUILDERS = {
    "branch_audit": (
        build_branch_audit_report,
        render_branch_audit_report_markdown,
    ),
    "merge_readiness": (
        build_merge_readiness_report,
        render_merge_readiness_report_markdown,
    ),
    "ai_worker_result_review": (
        build_ai_worker_result_review_packet,
        render_ai_worker_result_review_packet_markdown,
    ),
    "post_merge_retrospective": (
        build_post_merge_retrospective_report,
        render_post_merge_retrospective_report_markdown,
    ),
    "code_audit_daily": (
        build_code_audit_daily_report,
        render_code_audit_daily_report_markdown,
    ),
    "code_audit_operational_loop": (
        build_code_audit_operational_loop,
        render_code_audit_operational_loop_markdown,
    ),
}


class CodeAuditSamplePackTests(unittest.TestCase):
    def test_sample_pack_readme_exists(self):
        self.assertTrue((OUTPUT_DIR / "README.md").is_file())

    def test_all_sample_material_and_report_files_exist(self):
        for name in SPEC_BUILDERS:
            with self.subTest(name=name):
                self.assertTrue((OUTPUT_DIR / f"{name}_sample_material.json").is_file())
                self.assertTrue((OUTPUT_DIR / f"{name}_sample_report.md").is_file())

    def test_sample_material_json_is_parseable(self):
        for name in SPEC_BUILDERS:
            with self.subTest(name=name):
                payload = json.loads((OUTPUT_DIR / f"{name}_sample_material.json").read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)

    def test_generated_reports_match_rebuilt_outputs(self):
        for name, (builder, renderer) in SPEC_BUILDERS.items():
            with self.subTest(name=name):
                payload = json.loads((OUTPUT_DIR / f"{name}_sample_material.json").read_text(encoding="utf-8"))
                rebuilt = renderer(builder(deepcopy(payload), observed_at=OBSERVED_AT))
                checked_in = (OUTPUT_DIR / f"{name}_sample_report.md").read_text(encoding="utf-8")
                self.assertEqual(checked_in, rebuilt)

    def test_readme_says_sample_only_and_caller_provided_only(self):
        text = (OUTPUT_DIR / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("sample-only", text)
        self.assertIn("caller-provided material only", text)
        self.assertIn("nothing here proves live execution readiness", text)

    def test_reports_remain_sample_scoped_and_do_not_claim_actual_verification(self):
        for name in SPEC_BUILDERS:
            with self.subTest(name=name):
                text = (OUTPUT_DIR / f"{name}_sample_report.md").read_text(encoding="utf-8").lower()
                self.assertIn("sample", text)
                self.assertNotIn("actually verified", text)
                self.assertNotIn("live verification passed", text)

    def test_build_outputs_matches_checked_in_files(self):
        outputs = build_outputs()
        for path, content in outputs.items():
            with self.subTest(path=path.name):
                self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_generator_source_safety(self):
        source = Path("tools/generate_code_audit_sample_pack.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        banned_modules = {"subprocess", "socket", "requests", "httpx", "sqlite3", "dotenv"}
        banned_attr_names = {"system", "popen", "getenv"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], banned_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertIsNotNone(node.module)
                self.assertNotIn(str(node.module).split(".")[0], banned_modules)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.assertNotIn(func.id, {"load_dotenv", "getenv"})
                elif isinstance(func, ast.Attribute):
                    self.assertNotIn(func.attr, banned_attr_names)


if __name__ == "__main__":
    unittest.main()
