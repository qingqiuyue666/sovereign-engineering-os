import unittest

from kernel.status.status_reporter import v12_status_report


class StatusReporterV12Tests(unittest.TestCase):
    def test_report_is_machine_readable_and_deterministic(self):
        first = v12_status_report()
        second = v12_status_report()
        self.assertEqual(first, second)
        self.assertIn("security", first["implemented_modules"])
        self.assertIsInstance(first["forbidden_surfaces_absent"], dict)


if __name__ == "__main__":
    unittest.main()
