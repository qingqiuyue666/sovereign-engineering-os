import unittest

from kernel.errors.hierarchy import RetryExhaustedError
from kernel.retry.backoff import RetryConfig, exponential_backoff, retry, retry_call
from kernel.retry.policies import RetryPolicy, with_retry


class RetryBackoffTests(unittest.TestCase):
    def test_exponential_backoff_is_deterministic_and_bounded(self):
        config = RetryConfig(max_attempts=4, base_delay_seconds=0.5, max_delay_seconds=1.0, backoff_multiplier=2.0)
        self.assertEqual(exponential_backoff(1, config), 0.5)
        self.assertEqual(exponential_backoff(2, config), 1.0)
        self.assertEqual(exponential_backoff(3, config), 1.0)

    def test_retry_call_succeeds_after_retry_without_real_sleep(self):
        attempts = []
        sleeps = []

        def flaky():
            attempts.append("attempt")
            if len(attempts) == 1:
                raise ValueError("temporary")
            return "ok"

        result = retry_call(
            flaky,
            config=RetryConfig(max_attempts=3, base_delay_seconds=0.25, max_delay_seconds=1.0),
            operation_name="flaky",
            sleeper=sleeps.append,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.result, "ok")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(sleeps, [0.25])

    def test_retry_exhaustion_does_not_persist_raw_error_message(self):
        def fails():
            raise RuntimeError("secret_value=should_not_be_repeated")

        with self.assertRaises(RetryExhaustedError) as context:
            retry_call(
                fails,
                config=RetryConfig(max_attempts=2, base_delay_seconds=0.0),
                operation_name="no_raw_error",
                sleeper=lambda delay: None,
            )

        self.assertIn("RuntimeError", str(context.exception))
        self.assertNotIn("should_not_be_repeated", str(context.exception))

    def test_decorator_and_named_policy_use_unittest_safe_path(self):
        calls = []

        @with_retry(RetryPolicy.NO_RETRY, operation_name="decorated", sleeper=lambda delay: calls.append(delay))
        def succeeds():
            return 7

        self.assertEqual(succeeds().result, 7)
        self.assertEqual(calls, [])

        wrapped = retry(RetryConfig(max_attempts=1), operation_name="retry_decorator", sleeper=lambda delay: None)(lambda: "done")
        self.assertEqual(wrapped().result, "done")


if __name__ == "__main__":
    unittest.main()
