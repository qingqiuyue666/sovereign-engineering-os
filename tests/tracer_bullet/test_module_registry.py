import unittest

from kernel.status.module_registry import known_v12_modules


class ModuleRegistryTests(unittest.TestCase):
    def test_known_registry_reports_paths_and_missing_surfaces(self):
        modules = known_v12_modules()
        self.assertIn("security", modules)
        self.assertEqual(modules["security"]["path"], "kernel/security/secret_scanner.py")
        self.assertIn("dashboard", modules)
        self.assertIn("implemented", modules["dashboard"])


if __name__ == "__main__":
    unittest.main()
