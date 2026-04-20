from __future__ import annotations

from typing import Iterable, List

from app.config import DEFAULT_TOP_K
from app.knowledge_base import KnowledgeBase
from app.models import AnswerResponse, Citation, SearchResult
from app.safety import check_prompt, redact_sensitive_info


class KnowledgeAssistant:
    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.knowledge_base = knowledge_base

    def ask(self, question: str, top_k: int = DEFAULT_TOP_K) -> AnswerResponse:
        allowed, reason = check_prompt(question)
        if not allowed:
            return AnswerResponse(
                answer="This request is blocked by the assistant safety policy.",
                citations=[],
                safety_allowed=False,
                safety_reason=reason,
            )

        results = self.knowledge_base.search(question, top_k=top_k)
        if not results:
            return AnswerResponse(
                answer=(
                    "I could not find grounded guidance for that request in the current knowledge base. "
                    "Try a more specific product, policy, or error code question."
                ),
                citations=[],
                safety_allowed=True,
            )

        answer = self._compose_answer(question, results)
        citations = [
            Citation(
                chunk_id=result.chunk_id,
                title=result.title,
                snippet=redact_sensitive_info(result.snippet),
            )
            for result in results
        ]
        return AnswerResponse(
            answer=redact_sensitive_info(answer),
            citations=citations,
            safety_allowed=True,
        )

    def _compose_answer(self, question: str, results: List[SearchResult]) -> str:
        best_result = results[0]
        related_chunks = [
            self.knowledge_base.get_chunk(result.chunk_id)
            for result in results
        ]
        action_lines = self._extract_action_lines(
            chunk.text for chunk in related_chunks if chunk is not None
        )

        intro = (
            f"The strongest grounded match for '{question}' comes from '{best_result.title}' "
            f"under '{best_result.heading}'."
        )

        summary = (
            f"Key guidance: {best_result.snippet.rstrip('.')}."
            if best_result.snippet
            else "Key guidance is available in the cited source."
        )

        if action_lines:
            numbered_steps = "\n".join(
                f"{index}. {line}" for index, line in enumerate(action_lines[:4], start=1)
            )
            return (
                f"{intro}\n\n"
                f"{summary}\n\n"
                "Recommended next steps:\n"
                f"{numbered_steps}\n\n"
                "Use the citations below to verify the exact source wording."
            )

        return (
            f"{intro}\n\n"
            f"{summary}\n\n"
            "Use the citations below to verify the exact source wording."
        )

    @staticmethod
    def _extract_action_lines(chunks: Iterable[str]) -> List[str]:
        actions: List[str] = []
        seen = set()

        for text in chunks:
            for raw_line in text.splitlines():
                line = raw_line.strip(" -")
                if not line:
                    continue
                if raw_line.strip().startswith(tuple(str(number) for number in range(1, 10))):
                    cleaned = raw_line.strip().split(".", 1)[-1].strip()
                elif raw_line.strip().startswith("-"):
                    cleaned = line
                else:
                    continue
                normalized = cleaned.rstrip(".")
                if normalized.lower() in seen:
                    continue
                seen.add(normalized.lower())
                actions.append(normalized)

        return actions

