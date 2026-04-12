"""
AT-013: Replay claims must be bounded by captured evidence.

Constitutional anchors:
- v11 Section 22.5 Replay Fidelity Contract
- v11 Section 24.1 AT-013
- v11 Section 24.2 INV-010 (claims may not exceed captured evidence)
- v11 Section 24.2 INV-011 (uncertified equivalence is never exact replay)
- Foundation Section 5.1 test #7 (replay honesty, classification bound)

What this test proves:
  Missing evidence/inference artifact must downgrade or refuse exact
  replay claim. The classifier must never upgrade a claim beyond what
  the evidence supports.
"""

from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.replay.replay_classifier import (
    ReplayClass,
    ReplayClaimRequest,
    ReplayClassification,
    ReplayClassifier,
    EvidenceView,
)


class _FullEvidenceView:
    """Evidence view with all artifacts present."""

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return True

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return True

    def has_inference_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return True

    def required_artifact_ids(self, task_id: str, root_revision_id: str) -> list[str]:
        return ["ctx-1", "inf-1", "pp-1", "vr-1", "rv-1", "ap-1"]


class _MissingInferenceView:
    """Evidence view where inference artifact is missing."""

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return True

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return True

    def has_inference_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return False

    def required_artifact_ids(self, task_id: str, root_revision_id: str) -> list[str]:
        return ["ctx-1"]


class _MissingContextView:
    """Evidence view where context artifact is missing."""

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return True

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return False

    def has_inference_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return True

    def required_artifact_ids(self, task_id: str, root_revision_id: str) -> list[str]:
        return ["inf-1"]


class _NoSealedRevisionView:
    """Evidence view where no sealed revision exists."""

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return False

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return False

    def has_inference_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return False

    def required_artifact_ids(self, task_id: str, root_revision_id: str) -> list[str]:
        return []


class TestReplayClaimBound(unittest.TestCase):
    """AT-013 / INV-010 / INV-011: replay claims bounded by evidence."""

    def test_exact_replay_refused_without_full_evidence(self) -> None:
        """INV-011: exact replay requires full evidence; missing inference
        must downgrade."""
        classifier = ReplayClassifier(_MissingInferenceView())
        request = ReplayClaimRequest(
            task_id="t1",
            project_id="p1",
            root_revision_id="rev-1",
            requested_class=ReplayClass.EXACT,
            environment_fingerprint_hash="env:test",
        )
        result = classifier.classify(request)
        self.assertNotEqual(result.replay_class, ReplayClass.EXACT)
        self.assertIn(result.replay_class, [
            ReplayClass.DIAGNOSTIC,
            ReplayClass.SEMANTIC,
            ReplayClass.DEGRADED,
            ReplayClass.UNREPLAYABLE,
        ])

    def test_diagnostic_replay_succeeds_with_full_evidence(self) -> None:
        """DIAGNOSTIC replay with full evidence must classify at
        DIAGNOSTIC or better."""
        classifier = ReplayClassifier(_FullEvidenceView())
        request = ReplayClaimRequest(
            task_id="t1",
            project_id="p1",
            root_revision_id="rev-1",
            requested_class=ReplayClass.DIAGNOSTIC,
            environment_fingerprint_hash="env:test",
        )
        result = classifier.classify(request)
        self.assertIn(result.replay_class, [
            ReplayClass.EXACT, ReplayClass.DIAGNOSTIC,
        ])

    def test_missing_sealed_revision_is_unreplayable(self) -> None:
        """No sealed revision -> UNREPLAYABLE regardless of requested class."""
        classifier = ReplayClassifier(_NoSealedRevisionView())
        request = ReplayClaimRequest(
            task_id="t1",
            project_id="p1",
            root_revision_id="rev-1",
            requested_class=ReplayClass.DIAGNOSTIC,
            environment_fingerprint_hash="env:test",
        )
        result = classifier.classify(request)
        self.assertEqual(result.replay_class, ReplayClass.UNREPLAYABLE)

    def test_missing_context_degrades_semantic_to_degraded(self) -> None:
        """Missing context artifact must downgrade SEMANTIC to DEGRADED."""
        classifier = ReplayClassifier(_MissingContextView())
        request = ReplayClaimRequest(
            task_id="t1",
            project_id="p1",
            root_revision_id="rev-1",
            requested_class=ReplayClass.SEMANTIC,
            environment_fingerprint_hash="env:test",
        )
        result = classifier.classify(request)
        self.assertIn(result.replay_class, [
            ReplayClass.DEGRADED, ReplayClass.UNREPLAYABLE,
        ])

    def test_classifier_never_upgrades(self) -> None:
        """The classifier must never return a class higher than requested."""
        classifier = ReplayClassifier(_FullEvidenceView())
        request = ReplayClaimRequest(
            task_id="t1",
            project_id="p1",
            root_revision_id="rev-1",
            requested_class=ReplayClass.DEGRADED,
            environment_fingerprint_hash="env:test",
        )
        result = classifier.classify(request)
        # DEGRADED or lower (UNREPLAYABLE) only.
        class_order = [
            ReplayClass.EXACT, ReplayClass.DIAGNOSTIC,
            ReplayClass.SEMANTIC, ReplayClass.DEGRADED,
            ReplayClass.UNREPLAYABLE,
        ]
        requested_idx = class_order.index(ReplayClass.DEGRADED)
        result_idx = class_order.index(result.replay_class)
        self.assertGreaterEqual(result_idx, requested_idx)


if __name__ == "__main__":
    unittest.main()
