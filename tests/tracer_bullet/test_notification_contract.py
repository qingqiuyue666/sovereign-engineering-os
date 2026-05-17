import unittest

from kernel.notifications.notification_contract import validate_notification_envelope


class NotificationContractTests(unittest.TestCase):
    def test_notification_envelope_requires_digest(self):
        envelope = {"notification_id": "n1", "sink": "telegram_mock", "message_digest": "sha256:msg", "classification": "PUBLIC"}
        self.assertFalse(validate_notification_envelope(envelope))

    def test_blocks_secret_and_raw_message(self):
        envelope = {"notification_id": "n1", "sink": "telegram_mock", "message_digest": "sha256:msg", "classification": "SECRET", "raw_message": "x"}
        failures = validate_notification_envelope(envelope)
        self.assertIn("sensitive_notification_payload_forbidden", failures)
        self.assertIn("raw_message_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
