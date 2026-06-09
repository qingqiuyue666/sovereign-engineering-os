"""Behavior tests for repository-local skill registry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.skill_system import get_skill, load_skill_registry


class SkillSystemV1Tests(unittest.TestCase):
    def test_registry_loads_initial_repo_skills(self) -> None:
        registry = load_skill_registry()
        names = {skill["name"] for skill in registry["skills"]}
        self.assertIn("cross_dcc_workflow", names)
        self.assertIn("patch_repair", names)
        self.assertIn("output_packaging", names)

    def test_registry_validates_skill_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            write_json(root / "bad" / "skill.json", {"schema_version": "seos.skill.v1", "name": "bad"})
            with self.assertRaises(ValueError):
                load_skill_registry(root)

    def test_get_skill_returns_commands_and_runbook(self) -> None:
        skill = get_skill("cross_dcc_workflow")
        self.assertTrue(skill["commands"])
        self.assertEqual(skill["runbook"], "docs/runbooks/cross_software_workflow_engine.md")


if __name__ == "__main__":
    unittest.main()
