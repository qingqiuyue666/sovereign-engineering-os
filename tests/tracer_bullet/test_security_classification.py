import unittest

from kernel.security.security_classification import highest_classification, validate_classification


class SecurityClassificationTests(unittest.TestCase):
    def test_known_classification_is_accepted(self):
        result = validate_classification("secret")
        self.assertTrue(result.accepted)
        self.assertEqual(result.classification, "SECRET")

    def test_unknown_classification_fails_closed(self):
        result = validate_classification("public-ish")
        self.assertFalse(result.accepted)
        self.assertIn("classification_unknown", result.failures)

    def test_highest_unknown_escalates_to_crown_jewel(self):
        self.assertEqual(highest_classification(["PUBLIC", "CONFIDENTIAL"]), "CONFIDENTIAL")
        self.assertEqual(highest_classification(["PUBLIC", "mystery"]), "CROWN_JEWEL")


if __name__ == "__main__":
    unittest.main()
