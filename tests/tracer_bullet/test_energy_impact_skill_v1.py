"""Checks for the reusable energy_impact skill template."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from execution_plane.skill_system import get_skill


REPO_ROOT = Path(__file__).resolve().parents[2]


class EnergyImpactSkillV1Tests(unittest.TestCase):
    def test_skill_manifest_points_to_existing_templates(self) -> None:
        skill = get_skill("energy_impact", REPO_ROOT / "skills")

        self.assertEqual(skill["schema_version"], "seos.skill.v1")
        self.assertEqual(skill["name"], "energy_impact")
        self.assertIn("skills/energy_impact/runbook.md", skill["runbook"])
        for template_ref in skill["template_refs"]:
            self.assertTrue((REPO_ROOT / template_ref).exists(), template_ref)

    def test_skill_yaml_declares_required_adapters_configs_and_outputs(self) -> None:
        metadata = (REPO_ROOT / "skills/energy_impact/skill.yaml").read_text(encoding="utf-8")

        for required in (
            "purpose: first reusable Houdini + ComfyUI + DaVinci production shot template",
            "houdini_hython",
            "comfyui_local",
            "davinci_resolve",
            "required_configs:",
            "config/local_adapters/comfyui_local.json",
            "config/local_adapters/davinci_resolve.json",
            "config/local_adapters/houdini_hython.json",
            "Houdini cache/preview",
            "ComfyUI image output",
            "DaVinci project/version probe artifact",
            "SEOS package manifest",
            "review artifact",
            "runtime_output_policy:",
            "path refs only",
            "do not commit generated media",
        ):
            self.assertIn(required, metadata)

    def test_workflow_template_uses_expected_dcc_chain(self) -> None:
        workflow = json.loads((REPO_ROOT / "skills/energy_impact/workflows/energy_impact_workflow_v1.json").read_text(encoding="utf-8"))
        adapters = [node["adapter"] for node in workflow["nodes"]]
        actions = [node["action"] for node in workflow["nodes"]]

        self.assertEqual(adapters, ["houdini_hython", "comfyui_local", "davinci_resolve"])
        self.assertEqual(actions, ["smoke_cache_test", "submit_workflow", "project_probe"])
        self.assertEqual(workflow["edges"][0]["mode"], "artifact_refs")
        self.assertEqual(workflow["edges"][1]["mode"], "artifact_refs")
        for node in workflow["nodes"]:
            self.assertTrue((REPO_ROOT / node["rpc_template"]).exists(), node["rpc_template"])

    def test_rpc_chain_points_to_existing_rpc_templates(self) -> None:
        chain = json.loads((REPO_ROOT / "skills/energy_impact/rpc_templates/energy_impact_rpc_chain.json").read_text(encoding="utf-8"))

        self.assertEqual(chain["schema_version"], "seos.energy_impact.rpc_chain.v1")
        self.assertEqual([step["adapter"] for step in chain["steps"]], ["houdini_hython", "comfyui_local", "davinci_resolve"])
        for step in chain["steps"]:
            self.assertTrue((REPO_ROOT / step["template_path"]).exists(), step["template_path"])

    def test_directive_named_templates_exist_and_reference_examples(self) -> None:
        expected_refs = {
            "skills/energy_impact/rpc_templates/houdini_smoke_cache_test.json": "examples/rpc/houdini_smoke_cache_test.json",
            "skills/energy_impact/rpc_templates/comfyui_submit_workflow.json": "examples/rpc/comfyui_submit_workflow.json",
            "skills/energy_impact/rpc_templates/davinci_project_probe.json": "examples/rpc/davinci_project_probe.json",
        }
        for template_path, target_path in expected_refs.items():
            template = json.loads((REPO_ROOT / template_path).read_text(encoding="utf-8"))
            self.assertEqual(template["schema_version"], "seos.energy_impact.rpc_template_ref.v1")
            self.assertEqual(template["template_path"], target_path)
            self.assertTrue((REPO_ROOT / template["template_path"]).exists(), template["template_path"])

        self.assertTrue((REPO_ROOT / "skills/energy_impact/workflows/energy_impact_workflow_v1.json").exists())
        self.assertTrue((REPO_ROOT / "skills/energy_impact/prompts/energy_impact_prompt_v1.md").exists())


if __name__ == "__main__":
    unittest.main()
