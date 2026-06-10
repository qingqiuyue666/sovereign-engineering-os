"""Tests for failure bundle center integration V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.failure_bundle_center_integration import (
    FAILURE_BUNDLE_CRITICAL_KINDS,
    ZERO_HASH,
    FailureBundleCenterIntegrationError,
    FileBackedFailureBundleCenterIntegration,
    compute_failure_bundle_center_integrated_receipt_hash,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


SOURCE_PATH = Path("kernel/runtime/failure_bundle_center_integration.py")
TASK_ID = "task-519"
JOB_ID = "job-519"
RUN_ID = "run-519"
OBSERVED_AT = "2026-05-28T00:00:00+00:00"
RECOVERY_PLAN_HASH = "sha256:" + hashlib.sha256(b"recovery-plan").hexdigest()
SNAPSHOT_HASH = "sha256:" + hashlib.sha256(b"snapshot").hexdigest()

CONTEXT_FIELDS = (
    "task_context_hash",
    "job_context_hash",
    "run_context_hash",
    "wal_pointer_hash",
    "artifact_ids_hash",
    "replay_snapshot_context_hash",
    "approval_rejection_context_hash",
    "queue_transition_context_hash",
    "corruption_evidence_hash",
    "watchdog_failure_context_hash",
    "worker_failure_context_hash",
    "missing_record_context_hash",
    "hash_mismatch_context_hash",
)


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _contexts(**overrides: str) -> dict[str, str]:
    payload = {field: _hash(field) for field in CONTEXT_FIELDS}
    payload.update(overrides)
    return payload


class FailureBundleCenterIntegrationV1Tests(unittest.TestCase):
    def test_records_all_critical_failures_as_wal_artifact_manifest_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            center = FileBackedFailureBundleCenterIntegration(runtime_root=root)
            receipts = []
            for index, failure_kind in enumerate(FAILURE_BUNDLE_CRITICAL_KINDS, start=1):
                receipt = center.record_critical_failure(
                    failure_kind=failure_kind,
                    task_id=TASK_ID,
                    job_id=f"{JOB_ID}-{index}",
                    run_id=RUN_ID,
                    context_hashes=_contexts(),
                    recovery_plan_hash=RECOVERY_PLAN_HASH,
                    snapshot_reconstruction_hash=SNAPSHOT_HASH,
                    evidence_hashes={"operator_report_hash": _hash(f"operator-{index}")},
                    original_failure=RuntimeError("raw message must not be stored"),
                    observed_at=OBSERVED_AT,
                )
                persisted = center.read_persisted_bundle(receipt.failure_bundle_id)
                manifest = center.read_center_manifest(receipt.center_manifest_hash)
                receipts.append(receipt)

            wal_records = FileBackedRealWalStorage(
                root / "failure-bundle-center" / "failure.real-wal.jsonl"
            ).read_records()
            artifacts = FileBackedArtifactStore(
                root / "artifact-store",
                store_id="failure-bundle-center-artifacts-v1",
            ).read_records()

        self.assertEqual(len(receipts), len(FAILURE_BUNDLE_CRITICAL_KINDS))
        self.assertEqual(len(wal_records), len(FAILURE_BUNDLE_CRITICAL_KINDS))
        self.assertEqual(len(artifacts), len(FAILURE_BUNDLE_CRITICAL_KINDS))
        self.assertTrue(all(record.record_type == "FAILURE_BUNDLE_EVENT" for record in wal_records))
        self.assertTrue(all(receipt.accepted for receipt in receipts))
        self.assertTrue(all(not receipt.minimal_receipt for receipt in receipts))
        self.assertTrue(all(receipt.original_failure_type == "RuntimeError" for receipt in receipts))
        for receipt in receipts:
            self.assertEqual(
                receipt.receipt_hash,
                compute_failure_bundle_center_integrated_receipt_hash(receipt),
            )
            self.assertNotEqual(receipt.bundle_digest, ZERO_HASH)
            self.assertIn(receipt.failure_kind, FAILURE_BUNDLE_CRITICAL_KINDS)
        self.assertIn("bundle", persisted)
        self.assertEqual(manifest.manifest_hash, receipts[-1].center_manifest_hash)

    def test_missing_required_context_and_raw_material_fail_before_wal_append(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            center = FileBackedFailureBundleCenterIntegration(runtime_root=root)

            with self.assertRaisesRegex(
                FailureBundleCenterIntegrationError,
                "failure_context_missing:wal_pointer_hash",
            ):
                center.record_critical_failure(
                    failure_kind="wal_corruption",
                    task_id=TASK_ID,
                    job_id=JOB_ID,
                    run_id=RUN_ID,
                    context_hashes=_contexts(wal_pointer_hash=ZERO_HASH),
                    recovery_plan_hash=RECOVERY_PLAN_HASH,
                    snapshot_reconstruction_hash=SNAPSHOT_HASH,
                    observed_at=OBSERVED_AT,
                )
            with self.assertRaisesRegex(
                FailureBundleCenterIntegrationError,
                "evidence_hash_name_forbidden",
            ):
                center.record_critical_failure(
                    failure_kind="approval_rejection",
                    task_id=TASK_ID,
                    job_id=JOB_ID,
                    run_id=RUN_ID,
                    context_hashes=_contexts(),
                    recovery_plan_hash=RECOVERY_PLAN_HASH,
                    snapshot_reconstruction_hash=SNAPSHOT_HASH,
                    evidence_hashes={"raw_output_hash": _hash("raw-output")},
                    observed_at=OBSERVED_AT,
                )

            self.assertFalse(
                (root / "failure-bundle-center" / "failure.real-wal.jsonl").exists()
            )

    def test_write_failure_emits_minimal_safe_receipt_without_masking_original(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "artifact-store").write_text("not a directory", encoding="utf-8")
            center = FileBackedFailureBundleCenterIntegration(runtime_root=root)

            receipt = center.record_critical_failure(
                failure_kind="artifact_corruption",
                task_id=TASK_ID,
                job_id=JOB_ID,
                run_id=RUN_ID,
                context_hashes=_contexts(),
                recovery_plan_hash=RECOVERY_PLAN_HASH,
                snapshot_reconstruction_hash=SNAPSHOT_HASH,
                original_failure=KeyError("artifact payload omitted"),
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(receipt.accepted)
        self.assertTrue(receipt.minimal_receipt)
        self.assertEqual(receipt.original_failure_type, "KeyError")
        self.assertIn("failure_bundle_write_failed:ArtifactStorePersistenceError", receipt.failures)
        self.assertEqual(receipt.bundle_digest, ZERO_HASH)
        self.assertNotIn("artifact payload omitted", json.dumps(receipt.as_dict()))

    def test_tampered_persisted_bundle_replay_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            center = FileBackedFailureBundleCenterIntegration(runtime_root=root)
            receipt = center.record_critical_failure(
                failure_kind="hash_mismatch",
                task_id=TASK_ID,
                job_id=JOB_ID,
                run_id=RUN_ID,
                context_hashes=_contexts(),
                recovery_plan_hash=RECOVERY_PLAN_HASH,
                snapshot_reconstruction_hash=SNAPSHOT_HASH,
                observed_at=OBSERVED_AT,
            )
            path = (
                root
                / "failure-bundle-center"
                / "bundles"
                / (receipt.failure_bundle_id + ".json")
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["bundle"]["failure_code"] = "tampered"
            path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            with self.assertRaisesRegex(
                FailureBundleCenterIntegrationError,
                "failure_bundle_digest_mismatch",
            ):
                center.read_persisted_bundle(receipt.failure_bundle_id)

    def test_source_has_no_subprocess_network_provider_browser_or_env_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in ("shell=True", "os.system", "Popen", "os.environ", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
