import unittest

from kernel.errors.boundaries import ErrorBoundary, error_boundary
from kernel.errors.hierarchy import DaemonError, SovereignError


class ErrorHierarchyTests(unittest.TestCase):
    def test_error_dict_omits_message_by_default(self):
        error = DaemonError("raw provider detail should not be serialized by default")

        self.assertEqual(error.to_dict(), {"code": "DAEMON_ERROR", "type": "DaemonError"})
        self.assertIn("message", error.to_dict(include_message=True))

    def test_boundary_translates_unexpected_exception_without_raw_message(self):
        with self.assertRaises(SovereignError) as context:
            with ErrorBoundary("component"):
                raise ValueError("secret_value=do_not_copy")

        self.assertIn("ValueError", str(context.exception))
        self.assertNotIn("do_not_copy", str(context.exception))

    def test_boundary_preserves_existing_sovereign_error(self):
        with self.assertRaises(DaemonError):
            with ErrorBoundary("component", translate_to=DaemonError):
                raise DaemonError("daemon_failed")

    def test_explicit_suppress_is_required(self):
        with ErrorBoundary("component", translate_to=None, suppress=True) as boundary:
            raise ValueError("suppressed")

        self.assertEqual(boundary.caught_type, "ValueError")

    def test_decorator_translates(self):
        @error_boundary("decorated")
        def fails():
            raise RuntimeError("raw detail")

        with self.assertRaises(SovereignError):
            fails()


if __name__ == "__main__":
    unittest.main()
