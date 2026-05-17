import unittest

from kernel.replay.replay_verifier import verify_replay


class ReplayVerifierTests(unittest.TestCase):
    def manifest(self):
        return {"replay_id": "replay-1", "task_id": "task-1", "run_id": "run-1", "input_digest": "sha256:in", "policy_version": "v12", "code_version": "test", "event_digest_chain": ["sha256:a", "sha256:b"]}

    def test_digest_chain_match(self):
        result = verify_replay(self.manifest(), ["sha256:a", "sha256:b"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], "replay_match")

    def test_digest_chain_mismatch(self):
        result = verify_replay(self.manifest(), ["sha256:a", "sha256:c"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict"], "replay_mismatch")
        self.assertTrue(result["diff"]["changed"])


if __name__ == "__main__":
    unittest.main()
