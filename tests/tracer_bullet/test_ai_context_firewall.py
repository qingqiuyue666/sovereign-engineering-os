import unittest

from kernel.security.ai_context_firewall import filter_ai_context
from kernel.security.secret_scanner import REDACTION


class AIContextFirewallTests(unittest.TestCase):
    def test_preserves_dict_and_list_shape_while_redacting(self):
        context = {"safe": "ok", "nested": [{"token": "token=abc123456789SECRET"}]}
        result = filter_ai_context(context)
        self.assertTrue(result.accepted)
        self.assertEqual(set(result.filtered_context.keys()), {"safe", "nested"})
        self.assertEqual(result.filtered_context["nested"][0]["token"], REDACTION)
        self.assertEqual(context["nested"][0]["token"], "token=abc123456789SECRET")

    def test_clean_context_is_unchanged(self):
        context = {"digest": "sha256:abc", "items": [1, True, None]}
        result = filter_ai_context(context)
        self.assertEqual(result.filtered_context, context)
        self.assertEqual(result.redaction_count, 0)


if __name__ == "__main__":
    unittest.main()
