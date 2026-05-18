"""Tracer-bullet tests for ComfyUI workflow specifications."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.comfyui_workflow_spec import (
    COMFYUI_REQUIRED_INPUT_PASSES,
    ComfyUIWorkflowSpec,
    build_comfyui_workflow_spec,
    render_comfyui_workflow_spec_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "spec_id": "comfyui-workflow-spec-v1",
        "project_name": "VFX AI 3D Hybrid Sample",
        "input_passes": list(COMFYUI_REQUIRED_INPUT_PASSES),
        "control_maps": ["depth control", "normal control", "emission_or_mask control"],
        "style_reference_policy": ["bounded style reference", "no prompt-only generation"],
        "model_category_policy": ["no model download", "preapproved category notes only"],
        "denoise_policy": ["low-to-moderate denoise", "preserve controlled passes"],
        "node_group_requirements": ["input pass validation", "controlled enhancement"],
        "output_contract": {"review_frame": "summary only", "no_raw_output_persistence": True},
        "failure_cases": ["network attempt", "raw prompt persistence", "raw output persistence"],
        "review_criteria": ["no cheap AI artifact look", "no prompt-only generation"],
        "blocked_execution": [
            "No ComfyUI execution.",
            "No model download.",
            "No network.",
            "No raw prompt persistence.",
            "No raw output persistence.",
        ],
        "rollback_plan": ["revert ComfyUI workflow spec files as a unit"],
        "policy_version": "comfyui-workflow-spec-v1",
        "code_version": "0.1.0",
    }


class ComfyUIWorkflowSpecTests(unittest.TestCase):
    def test_valid_comfyui_spec_builds_deterministic_object(self):
        spec = build_comfyui_workflow_spec(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(spec, ComfyUIWorkflowSpec)
        self.assertTrue(spec.content_hash.startswith("sha256:"))
        self.assertEqual(spec.content_hash, digest_payload(spec.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_comfyui_workflow_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_comfyui_workflow_spec(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_comfyui_workflow_spec_markdown(
            build_comfyui_workflow_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_comfyui_workflow_spec_markdown(
            build_comfyui_workflow_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_required_input_pass_fails_closed(self):
        material = valid_material()
        material["input_passes"].remove("normal")

        with self.assertRaises(ValueError):
            build_comfyui_workflow_spec(material)

    def test_missing_control_maps_fails_closed(self):
        material = valid_material()
        del material["control_maps"]

        with self.assertRaises(ValueError):
            build_comfyui_workflow_spec(material)

    def test_missing_review_criteria_fails_closed(self):
        material = valid_material()
        del material["review_criteria"]

        with self.assertRaises(ValueError):
            build_comfyui_workflow_spec(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/comfyui_workflow_spec_v1.md").is_file())

    def test_doc_says_no_comfyui_model_network_execution(self):
        text = Path("docs/operator/comfyui_workflow_spec_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no comfyui/model/network execution", text)

    def test_doc_says_no_prompt_only_generation(self):
        text = Path("docs/operator/comfyui_workflow_spec_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no prompt-only generation", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/comfyui_workflow_spec.py").read_text(encoding="utf-8")

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
