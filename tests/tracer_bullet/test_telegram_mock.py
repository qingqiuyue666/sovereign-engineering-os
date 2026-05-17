import unittest

from kernel.notifications.telegram_mock import send_telegram_mock


class TelegramMockTests(unittest.TestCase):
    def test_mock_send_returns_receipt_no_live_send(self):
        envelope = {"notification_id": "n1", "sink": "telegram_mock", "message_digest": "sha256:msg", "classification": "PUBLIC", "redaction_status": "not_required"}
        result = send_telegram_mock(envelope)
        self.assertTrue(result["accepted"], result)
        self.assertFalse(result["live_send_performed"])
        self.assertEqual(result["receipt"]["sink"], "telegram_mock")


if __name__ == "__main__":
    unittest.main()
