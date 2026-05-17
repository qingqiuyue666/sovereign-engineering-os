import unittest

from kernel.tasks.run_id import canonical_json, deterministic_run_id, digest_payload


class RunIdTests(unittest.TestCase):
    def test_canonicalization_is_stable_across_key_ordering(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))
        self.assertEqual(digest_payload({"b": 2, "a": 1}), digest_payload({"a": 1, "b": 2}))

    def test_run_id_is_deterministic_from_declared_fields(self):
        first = deterministic_run_id(task_id="task-1", policy_version="v12", code_version="abc", input_digest="sha256:in")
        second = deterministic_run_id(task_id="task-1", policy_version="v12", code_version="abc", input_digest="sha256:in")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("run_"))


if __name__ == "__main__":
    unittest.main()
