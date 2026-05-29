"""Acceptance tests for Post-529 Operator Closure V1 runbook."""

from __future__ import annotations

import unittest

from tests.tracer_bullet.test_post_529_operator_closure_runbook_v1 import (
    ARTIFACT_PATHS,
    MANDATORY_COMMANDS,
    _runbook_text,
)


class Post529OperatorClosureRunbookV1AcceptanceTests(unittest.TestCase):
    def test_runbook_captures_operator_closure_contract(self) -> None:
        text = _runbook_text()
        for command in MANDATORY_COMMANDS:
            self.assertIn(command, text)
        for path in ARTIFACT_PATHS:
            self.assertIn(path, text)
        self.assertIn("Do not proceed", text)
        self.assertIn("P534 may generate a tag command proposal only", text)
        self.assertIn("P530 through P535", text)


if __name__ == "__main__":
    unittest.main()
