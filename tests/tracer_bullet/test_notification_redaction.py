import unittest

from kernel.notifications.notification_redaction import redact_notification_payload


class NotificationRedactionTests(unittest.TestCase):
    def test_redaction_before_send(self):
        result = redact_notification_payload({"message": "token=abc123456789SECRET"})
        self.assertEqual(result["redaction_status"], "redacted")
        self.assertEqual(result["redaction_count"], 1)


if __name__ == "__main__":
    unittest.main()
