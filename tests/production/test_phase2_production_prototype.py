from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
SHOTS = [
    "sword_slash_001",
    "smoke_burst_001",
    "portal_lightning_001",
    "impact_debris_001",
]
SKILLS = ["sword_slash", "smoke_burst", "portal_lightning", "impact_debris"]
REQUIRED_ADAPTERS = ["houdini_hython", "comfyui_local", "davinci_resolve"]
REQUIRED_ACTIONS = ["smoke_cache_test", "submit_workflow", "project_probe"]
EXPECTED_RUNTIME_ROOTS = {shot: f"work/phase2/{shot}" for shot in SHOTS}
EXPECTED_EVIDENCE = {
    "sword_slash_001": {
        "project_id": "PROJ_F99F99CEC6D9A214",
        "shot_id": "SHOT_91EF26FD49012F56",
        "run_id": "SHOTRUN_A9DE0747447C8972",
        "review_id": "REVIEW_46056859299892C2",
    },
    "smoke_burst_001": {
        "project_id": "PROJ_99407C637CCA8624",
        "shot_id": "SHOT_762544E82ACE38BB",
        "run_id": "SHOTRUN_21F05CEA307EDC58",
        "review_id": "REVIEW_2E3D8BEECBE7518E",
    },
    "portal_lightning_001": {
        "project_id": "PROJ_D515F70F38D6C892",
        "shot_id": "SHOT_F170AFA403E852EF",
        "run_id": "SHOTRUN_64B016BFBFA5C401",
        "review_id": "REVIEW_5EDC8971148739A0",
    },
    "impact_debris_001": {
        "project_id": "PROJ_F5F5FE4F81F0DF76",
        "shot_id": "SHOT_119E142029916DC8",
        "run_id": "SHOTRUN_08261BF4935B98E5",
        "review_id": "REVIEW_D6683C0D1B479C7B",
    },
}


class Phase2ProductionPrototypeTest(unittest.TestCase):
    def test_required_shot_files_exist_and_reference_safe_runtime_paths(self):
        for shot in SHOTS:
            project = ROOT / "examples" / "projects" / f"{shot}_project_v1.json"
            shot_dir = ROOT / "examples" / "shots" / shot
            for path in [project, shot_dir / "shot.json", shot_dir / "workflow.json", shot_dir / "README.md", ROOT / "docs" / "runbooks" / f"{shot}_real_shot.md"]:
                self.assertTrue(path.exists(), f"missing {path.relative_to(ROOT)}")
            project_payload = json.loads(project.read_text(encoding="utf-8"))
            self.assertEqual(project_payload["asset_strategy"]["large_outputs_committed"], False)
            self.assertEqual(project_payload["asset_strategy"]["local_runtime_root"], EXPECTED_RUNTIME_ROOTS[shot])
            self.assertEqual(project_payload["asset_strategy"]["copy_policy"], "path_refs_only")
            self.assertEqual(project_payload["dcc_adapters"], REQUIRED_ADAPTERS)
            shot_payload = json.loads((shot_dir / "shot.json").read_text(encoding="utf-8"))
            self.assertEqual(shot_payload["package_policy"]["runtime_outputs_committed"], False)
            self.assertEqual(shot_payload["package_policy"]["copy_policy"], "artifact_refs_only")
            self.assertEqual(shot_payload["project_template"], f"examples/projects/{shot}_project_v1.json")
            self.assertEqual(shot_payload["workflow"], f"examples/shots/{shot}/workflow.json")
            self.assertEqual([entry["adapter"] for entry in shot_payload["dcc_chain"]], REQUIRED_ADAPTERS)

    def test_workflows_use_required_existing_adapters(self):
        for shot in SHOTS:
            workflow = json.loads((ROOT / "examples" / "shots" / shot / "workflow.json").read_text(encoding="utf-8"))
            adapters = [node["adapter"] for node in workflow["nodes"]]
            self.assertEqual(adapters, REQUIRED_ADAPTERS)
            actions = [node["action"] for node in workflow["nodes"]]
            self.assertEqual(actions, REQUIRED_ACTIONS)
            self.assertEqual(len(workflow["edges"]), 2)
            self.assertTrue(all(edge["mode"] == "artifact_refs" for edge in workflow["edges"]))

    def test_required_skills_are_listable_manifests(self):
        for skill, shot in zip(SKILLS, SHOTS):
            path = ROOT / "skills" / skill / "skill.json"
            self.assertTrue(path.exists(), f"missing {path.relative_to(ROOT)}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "seos.skill.v1")
            self.assertEqual(payload["name"], skill)
            self.assertEqual(payload["adapters"], REQUIRED_ADAPTERS)
            commands = "\n".join(payload["commands"])
            self.assertIn("package run <run_id>", commands)
            self.assertIn("package shot <shot_id>", commands)
            self.assertIn("review create <shot_id>", commands)
            self.assertIn(f"work/phase2/{shot}", commands)
            self.assertTrue((ROOT / payload["runbook"]).exists())
            self.assertIn(f"examples/projects/{shot}_project_v1.json", payload["template_refs"])
            self.assertIn(f"examples/shots/{shot}/workflow.json", payload["template_refs"])
            self.assertIn("examples/rpc/houdini_smoke_cache_test.json", payload["template_refs"])
            self.assertIn("examples/rpc/comfyui_submit_workflow.json", payload["template_refs"])
            self.assertIn("examples/rpc/davinci_project_probe.json", payload["template_refs"])
            expected_outputs = "\n".join(payload.get("expected_outputs", []))
            self.assertIn("Houdini", expected_outputs)
            self.assertIn("ComfyUI", expected_outputs)
            self.assertIn("DaVinci", expected_outputs)
            self.assertIn("package manifest", expected_outputs)
            self.assertIn("review artifact", expected_outputs)

    def test_runbooks_and_readmes_record_no_runtime_commit_policy(self):
        for shot in SHOTS:
            docs = [
                ROOT / "docs" / "runbooks" / f"{shot}_real_shot.md",
                ROOT / "examples" / "shots" / shot / "README.md",
            ]
            for path in docs:
                text = path.read_text(encoding="utf-8")
                self.assertIn(EXPECTED_RUNTIME_ROOTS[shot], text)
                self.assertIn("must not be committed", text)
                self.assertIn("ArtifactRefs", text)
            runbook = docs[0].read_text(encoding="utf-8")
            self.assertIn("package run", runbook)
            self.assertIn("package shot", runbook)
            self.assertIn("review create", runbook)
            self.assertIn("execution_receipt.json", runbook)

    def test_phase2_report_records_real_evidence_and_no_stale_blocker(self):
        report = ROOT / "docs" / "reports" / "seos_phase2_production_report.md"
        self.assertTrue(report.exists())
        text = report.read_text(encoding="utf-8")
        self.assertNotIn("shell access is restored", text)
        self.assertNotIn("Cowork shell mount failure", text)
        self.assertNotIn("remaining blocker", text.lower())
        for shot, evidence in EXPECTED_EVIDENCE.items():
            self.assertIn(shot, text)
            self.assertIn("TERMINAL_SUCCEEDED", text)
            self.assertIn("ArtifactRefs", text)
            for value in evidence.values():
                self.assertIn(value, text)
        self.assertIn("python3 -m unittest discover -v", text)
        self.assertIn("make ci", text)
        self.assertIn("No runtime outputs are committed", text)


if __name__ == "__main__":
    unittest.main()
