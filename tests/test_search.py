from __future__ import annotations

import unittest

from app.assistant import KnowledgeAssistant
from app.knowledge_base import KnowledgeBase


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge_base = KnowledgeBase()
        cls.knowledge_base.rebuild()
        cls.assistant = KnowledgeAssistant(cls.knowledge_base)

    def test_wifi_query_returns_setup_guide(self) -> None:
        results = self.knowledge_base.search("How do I pair the oven with Wi-Fi?", top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0].document_id, "DOC-001")

    def test_error_query_returns_error_code_guide(self) -> None:
        results = self.knowledge_base.search("What does error E12 mean?", top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0].document_id, "DOC-003")

    def test_answer_contains_citations(self) -> None:
        response = self.assistant.ask("When do I escalate a premium support case?")
        self.assertTrue(response.safety_allowed)
        self.assertGreaterEqual(len(response.citations), 1)
        self.assertIn("premium support", response.answer.lower())


if __name__ == "__main__":
    unittest.main()
