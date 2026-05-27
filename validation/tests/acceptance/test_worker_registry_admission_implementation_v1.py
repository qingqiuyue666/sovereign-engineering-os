import json
import unittest

from kernel.os_engine.worker_registry import (
    GitWorker,
    WorkerAdmissionError,
    WorkerRegistry,
    build_default_worker_registry,
    evaluate_worker_admission,
)


class UnsupportedWorker:
    name = "UnsupportedWorker"
    capabilities = frozenset({"network_shell"})
    safety_boundary = "unsafe"
    can_create_large_artifacts = False
    human_review_required = False


class WorkerRegistryAdmissionImplementationAcceptanceTests(unittest.TestCase):
    def test_default_worker_registry_records_admission_decisions(self):
        registry = build_default_worker_registry()
        report = json.loads(registry.admission_report_json())

        self.assertTrue(report)
        self.assertTrue(all(item["accepted"] for item in report))
        self.assertTrue(all(item["content_hash"].startswith("sha256:") for item in report))
        self.assertTrue(any(item["worker_type"] == "git" for item in report))

    def test_rejected_worker_admission_is_available_without_registry_mutation(self):
        registry = WorkerRegistry()
        decision = evaluate_worker_admission("unsafe", UnsupportedWorker())

        self.assertFalse(decision.accepted)
        self.assertIn("unsupported_capability:network_shell", decision.reason_codes)
        self.assertEqual(registry.registered_types(), [])
        with self.assertRaises(WorkerAdmissionError):
            registry.register("unsafe", UnsupportedWorker())  # type: ignore[arg-type]
        self.assertEqual(registry.registered_types(), [])

    def test_duplicate_worker_type_fails_closed(self):
        registry = WorkerRegistry()
        registry.register("git", GitWorker())
        duplicate = evaluate_worker_admission(
            "git",
            GitWorker(),
            registered_types=registry.registered_types(),
        )

        self.assertFalse(duplicate.accepted)
        self.assertIn("duplicate_worker_type", duplicate.reason_codes)


if __name__ == "__main__":
    unittest.main()
