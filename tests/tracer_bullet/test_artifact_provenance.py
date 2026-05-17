import unittest

from kernel.security.artifact_provenance import validate_artifact_provenance


class ArtifactProvenanceTests(unittest.TestCase):
    def valid_record(self):
        return {
            "artifact_id": "art-1",
            "artifact_type": "dry_run_result",
            "content_hash": "sha256:abc",
            "source_refs": ["input:1"],
            "classification": "INTERNAL",
            "created_by_stage": "dry_run",
        }

    def test_valid_provenance_is_accepted(self):
        self.assertTrue(validate_artifact_provenance(self.valid_record()).accepted)

    def test_requires_digest_and_source_refs(self):
        record = self.valid_record()
        record["content_hash"] = "raw"
        record["source_refs"] = []
        result = validate_artifact_provenance(record)
        self.assertFalse(result.accepted)
        self.assertIn("content_hash_must_be_digest_ref", result.failures)
        self.assertIn("source_refs_must_be_nonempty_string_list", result.failures)

    def test_raw_content_is_forbidden(self):
        record = self.valid_record()
        record["raw_content"] = "secret"
        self.assertIn("raw_content_forbidden", validate_artifact_provenance(record).failures)


if __name__ == "__main__":
    unittest.main()
