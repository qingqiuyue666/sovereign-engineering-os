import base64
import hashlib
import unittest

from kernel.security.secret_scanner import CoreSecretScanner, SAFE_TEST_MARKER


class CoreSecretScannerTests(unittest.TestCase):
    def test_detects_secret_like_assignment(self):
        result = CoreSecretScanner().scan_text("api_key = 'abc123456789SECRET'")
        self.assertFalse(result.clean)
        self.assertIn("assignment_secret", {finding.kind for finding in result.findings})

    def test_fake_marker_only_allowed_in_tests_or_fixture_path(self):
        scanner = CoreSecretScanner()
        self.assertTrue(scanner.scan_text(SAFE_TEST_MARKER, path="tests/example.txt").clean)
        self.assertTrue(scanner.scan_text(SAFE_TEST_MARKER, path="governance/security/fixtures/example.txt").clean)
        self.assertFalse(scanner.scan_text(SAFE_TEST_MARKER, path="docs/example.md").clean)

    def test_known_safe_hash_allowlist(self):
        digest = hashlib.sha256(b"api_key = 'abc123456789SECRET'").hexdigest()
        scanner = CoreSecretScanner(known_safe_hashes={digest})
        self.assertTrue(scanner.scan_text("api_key = 'abc123456789SECRET'").clean)

    def test_bounded_base64_decode_finds_encoded_secret(self):
        encoded = base64.b64encode(b"token=abc123456789SECRET").decode("ascii")
        result = CoreSecretScanner().scan_text(encoded)
        self.assertFalse(result.clean)
        self.assertIn("decoded_assignment_secret", {finding.kind for finding in result.findings})

    def test_limits_scan_size_without_regex_blowup(self):
        scanner = CoreSecretScanner(max_text_chars=10, max_scan_items=3)
        result = scanner.scan_text("x" * 10000)
        self.assertTrue(result.clean)
        self.assertTrue(result.truncated)
        self.assertEqual(result.scanned_text_chars, 10)


if __name__ == "__main__":
    unittest.main()
