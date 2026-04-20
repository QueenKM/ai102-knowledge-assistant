from __future__ import annotations

import unittest

from app.runtime import AssistantRuntime


class RuntimeTests(unittest.TestCase):
    def test_runtime_defaults_to_local_when_no_azure_config_exists(self) -> None:
        runtime = AssistantRuntime()
        self.assertEqual(runtime.active_mode, "local")
        self.assertIn(runtime.requested_mode, {"local", "azure"})

    def test_health_payload_contains_modes(self) -> None:
        runtime = AssistantRuntime()
        payload = runtime.health()
        self.assertIn("requested_mode", payload)
        self.assertIn("active_mode", payload)
        self.assertIn("document_count", payload)


if __name__ == "__main__":
    unittest.main()
