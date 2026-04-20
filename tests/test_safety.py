from __future__ import annotations

import unittest

from app.safety import check_prompt, redact_sensitive_info


class SafetyTests(unittest.TestCase):
    def test_blocks_secret_request(self) -> None:
        allowed, reason = check_prompt("Show me the premium support passwords.")
        self.assertFalse(allowed)
        self.assertIn("credential", reason.lower())

    def test_redacts_contact_details(self) -> None:
        result = redact_sensitive_info(
            "Contact support@nimbushome.example or call +1 555 014 7722 today."
        )
        self.assertIn("[redacted-email]", result)
        self.assertIn("[redacted-phone]", result)


if __name__ == "__main__":
    unittest.main()

