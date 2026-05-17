import json
import subprocess
import sys
import unittest


class CLIStatusTests(unittest.TestCase):
    def test_health_plan_and_version_are_deterministic(self):
        plan = subprocess.run([sys.executable, "seos.py", "health-plan"], check=False, capture_output=True, text=True)
        version = subprocess.run([sys.executable, "seos.py", "version"], check=False, capture_output=True, text=True)
        self.assertEqual(plan.returncode, 0)
        self.assertIn("test-leak-prevention-foundation", json.loads(plan.stdout)["health_plan"])
        self.assertEqual(json.loads(version.stdout)["version"], "v12-foundation-draft")


if __name__ == "__main__":
    unittest.main()
