import unittest

from kernel.tasks.task_manifest import validate_task_manifest


class TaskManifestTests(unittest.TestCase):
    def valid_manifest(self):
        return {
            "objective": "dry-run a digest-only task",
            "requested_capabilities": ["local_dry_run"],
            "classification": "INTERNAL",
            "policy_version": "v12",
            "code_version": "test",
            "input_digest": "sha256:abc",
        }

    def test_assigns_deterministic_task_id_if_missing(self):
        first = validate_task_manifest(self.valid_manifest())
        second = validate_task_manifest(dict(reversed(list(self.valid_manifest().items()))))
        self.assertTrue(first.accepted, first.failures)
        self.assertEqual(first.manifest["task_id"], second.manifest["task_id"])

    def test_requires_capabilities_and_classification(self):
        result = validate_task_manifest({"objective": "x", "policy_version": "v12", "code_version": "test", "input_digest": "sha256:abc"})
        self.assertFalse(result.accepted)
        self.assertIn("requested_capabilities_required", result.failures)
        self.assertIn("classification_required", result.failures)

    def test_rejects_provider_bound_sensitive_task(self):
        manifest = self.valid_manifest()
        manifest["requested_capabilities"] = ["provider_adapter"]
        manifest["classification"] = "SECRET"
        self.assertIn("provider_bound_sensitive_task_forbidden", validate_task_manifest(manifest).failures)


if __name__ == "__main__":
    unittest.main()
