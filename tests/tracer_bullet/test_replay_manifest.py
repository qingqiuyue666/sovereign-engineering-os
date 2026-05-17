import unittest

from kernel.replay.replay_manifest import validate_replay_manifest


class ReplayManifestTests(unittest.TestCase):
    def manifest(self):
        return {"replay_id": "replay-1", "task_id": "task-1", "run_id": "run-1", "input_digest": "sha256:in", "policy_version": "v12", "code_version": "test", "event_digest_chain": ["sha256:a"]}

    def test_valid_manifest_is_accepted(self):
        self.assertTrue(validate_replay_manifest(self.manifest()).accepted)

    def test_rejects_missing_versions_and_provider_requery(self):
        manifest = self.manifest()
        del manifest["policy_version"]
        del manifest["code_version"]
        manifest["provider_requery_requested"] = True
        result = validate_replay_manifest(manifest)
        self.assertIn("policy_version_required", result.failures)
        self.assertIn("code_version_required", result.failures)
        self.assertIn("provider_requery_forbidden", result.failures)


if __name__ == "__main__":
    unittest.main()
