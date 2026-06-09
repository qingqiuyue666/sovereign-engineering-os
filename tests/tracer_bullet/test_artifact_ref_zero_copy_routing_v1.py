"""Tests for ArtifactRef zero-copy routing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.runtime.artifact_router import (
    attach_artifacts_to_payload,
    build_routing_receipt,
    refs_from_outputs,
    route_artifacts,
    validate_artifact_ref,
)
from execution_plane.runner.result_envelope import collect_output_records, sha256_file


class ArtifactRefZeroCopyRoutingV1Tests(unittest.TestCase):
    def test_path_ref_creation_has_required_model_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "image.png").write_bytes(b"image")
            refs = refs_from_outputs(
                run_id="RUN_PRODUCER",
                node_id="producer",
                output_records=collect_output_records(root),
            )
        self.assertEqual(len(refs), 1)
        self.assertTrue(validate_artifact_ref(refs[0]))
        self.assertEqual(refs[0]["storage_mode"], "path_ref")

    def test_downstream_consumption_receives_artifact_refs(self) -> None:
        ref = _ref()
        route = route_artifacts(artifact_refs=[ref], downstream_node_id="downstream")
        payload = attach_artifacts_to_payload({"mode": "consume"}, route)
        self.assertEqual(payload["artifact_refs"][0]["artifact_id"], ref["artifact_id"])
        self.assertEqual(route["storage_mode"], "path_ref")

    def test_no_duplicate_copy_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "producer"
            root.mkdir()
            (root / "plate.png").write_bytes(b"plate")
            ref = refs_from_outputs(run_id="RUN_A", node_id="producer", output_records=collect_output_records(root))[0]
            copy_root = Path(tempdir) / "copy"
            route = route_artifacts(
                artifact_refs=[ref],
                downstream_node_id="consumer",
                source_root=root,
                managed_copy_root=copy_root,
            )
        self.assertEqual(route["copied_files"], [])
        self.assertFalse(copy_root.exists())

    def test_managed_copy_requested_copies_selected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "producer"
            copy_root = Path(tempdir) / "managed"
            root.mkdir()
            artifact = root / "plate.png"
            artifact.write_bytes(b"plate")
            original_hash = sha256_file(artifact)
            ref = refs_from_outputs(run_id="RUN_A", node_id="producer", output_records=collect_output_records(root))[0]
            route = route_artifacts(
                artifact_refs=[ref],
                downstream_node_id="consumer",
                source_root=root,
                managed_copy_root=copy_root,
                storage_mode="managed_copy",
            )
            copied_path = copy_root / "plate.png"
            copied_exists = copied_path.exists()
            copied_hash = sha256_file(copied_path)
        self.assertTrue(copied_exists)
        self.assertEqual(copied_hash, original_hash)
        self.assertEqual(route["artifact_refs"][0]["storage_mode"], "managed_copy")

    def test_receipt_contains_artifact_ref_and_preserves_hash(self) -> None:
        ref = _ref(sha256="sha256:" + "a" * 64)
        route = route_artifacts(artifact_refs=[ref], downstream_node_id="downstream")
        with tempfile.TemporaryDirectory() as tempdir:
            receipt_path = Path(tempdir) / "routing_receipt.json"
            receipt = build_routing_receipt(route=route, receipt_path=receipt_path)
            loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["artifact_refs"][0]["sha256"], ref["sha256"])
        self.assertEqual(loaded["artifact_refs"][0]["artifact_id"], ref["artifact_id"])


def _ref(*, sha256: str = "sha256:" + "0" * 64) -> dict[str, object]:
    return {
        "schema_version": "seos.artifact_ref.v1",
        "artifact_id": "ART_TEST",
        "producer_run_id": "RUN_TEST",
        "producer_node_id": "producer",
        "uri": "seos://run/RUN_TEST/plate.png",
        "relative_path": "plate.png",
        "size_bytes": 5,
        "sha256": sha256,
        "media_type": "image/png",
        "storage_mode": "path_ref",
        "copy_policy": "zero_copy_reference",
        "lifetime": "managed_by_run_package",
    }


if __name__ == "__main__":
    unittest.main()
