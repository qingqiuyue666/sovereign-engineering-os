import unittest

from kernel.replay.replay_diff import diff_digest_chains


class ReplayDiffTests(unittest.TestCase):
    def test_reports_missing_extra_and_changed_digest_entries(self):
        diff = diff_digest_chains(["sha256:a", "sha256:b"], ["sha256:a", "sha256:c", "sha256:d"])
        self.assertEqual(diff["missing"], ["sha256:b"])
        self.assertEqual(diff["extra"], ["sha256:c", "sha256:d"])
        self.assertEqual(diff["changed"][0]["index"], 1)


if __name__ == "__main__":
    unittest.main()
