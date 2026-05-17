import json
import subprocess
import sys
import unittest


class CLISecurityScanTests(unittest.TestCase):
    def test_security_scan_text_uses_core_scanner(self):
        result = subprocess.run([sys.executable, "seos.py", "security-scan-text", "token=abc123456789SECRET"], check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("assignment_secret", payload["findings"])


if __name__ == "__main__":
    unittest.main()
