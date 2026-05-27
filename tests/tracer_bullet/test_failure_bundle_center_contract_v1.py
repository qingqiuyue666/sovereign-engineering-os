"""Tracer-bullet tests for failure bundle center contract v1."""

from dataclasses import replace
from pathlib import Path
import unittest

from kernel.runtime.failure_bundle_center_contract import (
    build_failure_bundle_center_manifest,
    build_failure_bundle_reference,
    validate_failure_bundle_center_manifest,
    validate_failure_bundle_reference,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64
D5 = "sha256:" + "5" * 64
D6 = "sha256:" + "6" * 64
D7 = "sha256:" + "7" * 64
D8 = "sha256:" + "8" * 64
D9 = "sha256:" + "9" * 64
DA = "sha256:" + "a" * 64
DB = "sha256:" + "b" * 64


class FailureBundleCenterContractV1Tests(unittest.TestCase):
    def _reference_payload(
        self,
        *,
        failure_bundle_id: str = "failure-bundle-001",
        severity: str = "terminal",
        retry_decision: str = "no_retry_terminal",
        quarantine_required: bool = True,
    ) -> dict[str, object]:
        return {
            "failure_bundle_id": failure_bundle_id,
            "task_id": "task-001",
            "run_id": "run-001",
            "failure_stage": "preflight",
            "failure_code": "wal_append_failed",
            "failure_class": "policy_failure",
            "severity": severity,
            "retry_decision": retry_decision,
            "bundle_digest": D1,
            "wal_record_hash": D2,
            "artifact_manifest_hash": D3,
            "snapshot_reconstruction_hash": D4,
            "recovery_plan_hash": D5,
            "stdout_digest": D6,
            "stderr_digest": D7,
            "stdout_truncated": False,
            "stderr_truncated": True,
            "quarantine_required": quarantine_required,
        }

    def test_reference_hash_is_deterministic_and_excludes_observed_at(self):
        first = build_failure_bundle_reference(
            self._reference_payload(),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_failure_bundle_reference(
            self._reference_payload(),
            observed_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_failure_bundle_reference(first))
        self.assertEqual(first.reference_hash, second.reference_hash)
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertNotIn("observed_at", first.deterministic_material())

    def test_reference_rejects_raw_output_traceback_secret_and_execution_material(self):
        forbidden_payloads = [
            {"stdout": "raw output"},
            {"stderr": "raw error"},
            {"raw_traceback": "trace"},
            {"secret_value": "secret"},
            {"env": {"TOKEN": "value"}},
            {"argv": ["python"]},
            {"filesystem_path": "/tmp/failure.json"},
            {"payload": {"unsafe": True}},
        ]

        for forbidden in forbidden_payloads:
            payload = self._reference_payload()
            payload.update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    build_failure_bundle_reference(payload)

    def test_reference_accepts_digest_only_output_bindings(self):
        reference = build_failure_bundle_reference(self._reference_payload())

        self.assertEqual(reference.stdout_digest, D6)
        self.assertEqual(reference.stderr_digest, D7)
        self.assertFalse(reference.stdout_truncated)
        self.assertTrue(reference.stderr_truncated)

    def test_terminal_failures_require_quarantine_and_no_retry(self):
        missing_quarantine = self._reference_payload(quarantine_required=False)
        with self.assertRaises(ValueError):
            build_failure_bundle_reference(missing_quarantine)

        bad_retry = self._reference_payload(retry_decision="retry_after_backoff")
        with self.assertRaises(ValueError):
            build_failure_bundle_reference(bad_retry)

    def test_retryable_failures_require_retry_after_backoff(self):
        payload = self._reference_payload(
            severity="retryable",
            retry_decision="retry_after_backoff",
            quarantine_required=False,
        )
        reference = build_failure_bundle_reference(payload)
        self.assertTrue(validate_failure_bundle_reference(reference))

        bad_retry = self._reference_payload(
            severity="retryable",
            retry_decision="manual_review_required",
            quarantine_required=False,
        )
        with self.assertRaises(ValueError):
            build_failure_bundle_reference(bad_retry)

    def test_manifest_aggregates_references_and_counts_failure_classes(self):
        terminal = build_failure_bundle_reference(self._reference_payload())
        retryable_payload = self._reference_payload(
            failure_bundle_id="failure-bundle-002",
            severity="retryable",
            retry_decision="retry_after_backoff",
            quarantine_required=False,
        )
        retryable_payload["bundle_digest"] = D8
        retryable_payload["wal_record_hash"] = D9
        retryable = build_failure_bundle_reference(retryable_payload)

        manifest = build_failure_bundle_center_manifest(
            manifest_id="failure-center-001",
            task_id="task-001",
            run_id="run-001",
            wal_head_hash=DA,
            recovery_plan_hash=D5,
            references=(terminal, retryable),
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertTrue(validate_failure_bundle_center_manifest(manifest))
        self.assertEqual(manifest.retryable_failure_count, 1)
        self.assertEqual(manifest.terminal_failure_count, 1)
        self.assertTrue(manifest.quarantine_required)
        self.assertEqual(
            manifest.failure_reference_hashes,
            (terminal.reference_hash, retryable.reference_hash),
        )

    def test_manifest_rejects_identity_mismatch_duplicate_and_recovery_mismatch(self):
        reference = build_failure_bundle_reference(self._reference_payload())

        with self.assertRaises(ValueError):
            build_failure_bundle_center_manifest(
                manifest_id="failure-center-001",
                task_id="other-task",
                run_id="run-001",
                wal_head_hash=DA,
                recovery_plan_hash=D5,
                references=(reference,),
            )
        with self.assertRaises(ValueError):
            build_failure_bundle_center_manifest(
                manifest_id="failure-center-001",
                task_id="task-001",
                run_id="run-001",
                wal_head_hash=DA,
                recovery_plan_hash=D5,
                references=(reference, reference),
            )
        with self.assertRaises(ValueError):
            build_failure_bundle_center_manifest(
                manifest_id="failure-center-001",
                task_id="task-001",
                run_id="run-001",
                wal_head_hash=DA,
                recovery_plan_hash=DB,
                references=(reference,),
            )

    def test_validators_reject_tampered_hashes_and_counts(self):
        reference = build_failure_bundle_reference(self._reference_payload())
        self.assertFalse(validate_failure_bundle_reference(replace(reference, reference_hash=DA)))

        manifest = build_failure_bundle_center_manifest(
            manifest_id="failure-center-001",
            task_id="task-001",
            run_id="run-001",
            wal_head_hash=DA,
            recovery_plan_hash=D5,
            references=(reference,),
        )
        self.assertFalse(validate_failure_bundle_center_manifest(replace(manifest, manifest_hash=DB)))
        self.assertFalse(
            validate_failure_bundle_center_manifest(
                replace(manifest, retryable_failure_count=-1)
            )
        )

    def test_source_has_no_storage_execution_provider_or_daemon_surface(self):
        source = Path("kernel/runtime/failure_bundle_center_contract.py").read_text()

        forbidden = [
            "sqlite3",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "argparse",
            "click",
            "typer",
            "daemon",
            "os.environ",
            "Path(",
            "open(",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
