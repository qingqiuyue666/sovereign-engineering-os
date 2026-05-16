import base64
import unittest

from kernel.security.secret_scanner import CoreSecretScanner, FAKE_MARKER


class SecretScannerTests(unittest.TestCase):
    def setUp(self):
        self.scanner = CoreSecretScanner(max_text_chars=1000, max_file_bytes=1024, max_scan_items=20)

    def test_scanner_catches_sensitive_label_patterns(self):
        result = self.scanner.scan_text("api_key = value", path="docs/example.txt")
        self.assertFalse(result.accepted)
        self.assertTrue(any(f.finding_type == "sensitive_label" for f in result.findings))

    def test_scanner_catches_private_material_block(self):
        result = self.scanner.scan_text("-----BEGIN PRIVATE MATERIAL-----", path="docs/example.txt")
        self.assertFalse(result.accepted)
        self.assertTrue(any(f.finding_type == "private_material_block" for f in result.findings))

    def test_scanner_catches_base64_encoded_sensitive_label(self):
        encoded = base64.b64encode(b"token = value").decode("ascii")
        result = self.scanner.scan_text(encoded, path="docs/example.txt")
        self.assertFalse(result.accepted)
        self.assertTrue(any("base64" in f.field for f in result.findings))

    def test_scanner_rejects_fake_marker_outside_tests(self):
        result = self.scanner.scan_text(FAKE_MARKER, path="kernel/example.py")
        self.assertFalse(result.accepted)
        self.assertIn("fake_marker_outside_allowed_path", {f.finding_type for f in result.findings})

    def test_scanner_allows_fake_marker_inside_tests(self):
        result = self.scanner.scan_text(FAKE_MARKER, path="tests/fixtures/example.txt")
        self.assertTrue(result.accepted, result.findings)

    def test_mapping_ignores_known_safe_hash_fields(self):
        payload = {"git_blob_sha1": "a141375ed472b484c01671d05f6d375be3d9ed27"}
        result = self.scanner.scan_mapping(payload)
        self.assertTrue(result.accepted, result.findings)

    def test_mapping_blocks_dangerous_field_name(self):
        result = self.scanner.scan_mapping({"token": "redacted"})
        self.assertFalse(result.accepted)
        self.assertIn("dangerous_field_name", {f.finding_type for f in result.findings})

    def test_scanner_flags_large_file_metadata(self):
        result = self.scanner.scan_file_metadata(path="large.log", size_bytes=2048)
        self.assertFalse(result.accepted)
        self.assertIn("file_too_large", {f.finding_type for f in result.findings})


if __name__ == "__main__":
    unittest.main()
