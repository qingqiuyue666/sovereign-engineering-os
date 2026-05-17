
#!/usr/bin/env python3

"""Generate a bounded local-only code stage example.

This script writes only allowlisted files declared in

governance/local_train/code_stage_registry_v1.json.

It does not call cloud AI.

It does not read secrets.

It does not run shell commands.

It does not mutate git state.

"""

from __future__ import annotations

import json

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DOC = ROOT / "docs/runbooks/generated_local_code_stage_example_v1.md"

OUTPUT_POLICY = ROOT / "governance/local_train/generated_local_code_stage_example_v1.json"

OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_generated_local_code_stage_example.py"

ALLOWED_OUTPUTS = {

    OUTPUT_DOC,

    OUTPUT_POLICY,

    OUTPUT_TEST,

}

def assert_allowed(path: Path) -> None:

    resolved = path.resolve()

    allowed = {item.resolve() for item in ALLOWED_OUTPUTS}

    if resolved not in allowed:

        raise RuntimeError(f"write_path_not_allowlisted: {path}")

def write(path: Path, text: str) -> None:

    assert_allowed(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(text, encoding="utf-8")

def main() -> int:

    policy = {

        "artifact_name": "generated_local_code_stage_example_v1",

        "artifact_version": "v1",

        "status": "active",

        "purpose": "Prove bounded local-only code generation through an allowlisted stage script.",

        "generated_by": "tools/local_code_stages/generate_local_code_stage_example.py",

        "cloud_ai_used": False,

        "freeform_shell_used": False,

        "secret_read": False,

        "allowed_outputs": [

            "docs/runbooks/generated_local_code_stage_example_v1.md",

            "governance/local_train/generated_local_code_stage_example_v1.json",

            "tests/tracer_bullet/test_generated_local_code_stage_example.py",

        ],

    }

    write(

        OUTPUT_POLICY,

        json.dumps(policy, indent=2, sort_keys=True) + "\n",

    )

    write(

        OUTPUT_DOC,

        """# Generated Local Code Stage Example v1

## Purpose

This file proves that the autonomous code stage can generate bounded local artifacts through a predefined local script.

## Boundaries

- no cloud AI

- no freeform shell

- no secret reads

- no provider live execution

- no vault live write

- no production autonomy

- no git merge

- no push main

- no branch deletion

## Scope

This is an example artifact only.

It does not implement production runtime behavior.

""",

    )

    write(

        OUTPUT_TEST,

        '''"""Tests for generated local code stage example."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

DOC = Path("docs/runbooks/generated_local_code_stage_example_v1.md")

POLICY = Path("governance/local_train/generated_local_code_stage_example_v1.json")

class GeneratedLocalCodeStageExampleTests(unittest.TestCase):

    def test_generated_files_exist(self):

        self.assertTrue(DOC.is_file())

        self.assertTrue(POLICY.is_file())

    def test_generated_policy_is_active_and_local_only(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["artifact_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertFalse(payload["cloud_ai_used"])

        self.assertFalse(payload["freeform_shell_used"])

        self.assertFalse(payload["secret_read"])

    def test_generated_doc_records_boundaries(self):

        text = DOC.read_text(encoding="utf-8")

        self.assertIn("no cloud AI", text)

        self.assertIn("no freeform shell", text)

        self.assertIn("no secret reads", text)

        self.assertIn("does not implement production runtime behavior", text)

if __name__ == "__main__":

    unittest.main()

''',

    )

    return 0

if __name__ == "__main__":

    raise SystemExit(main())

