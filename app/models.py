from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class Document:
    document_id: str
    title: str
    category: str
    audience: str
    path: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    heading: str
    category: str
    text: str
    tokens: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    title: str
    heading: str
    category: str
    score: float
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Citation:
    chunk_id: str
    title: str
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnswerResponse:
    answer: str
    citations: List[Citation]
    safety_allowed: bool
    safety_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "safety_allowed": self.safety_allowed,
            "safety_reason": self.safety_reason,
        }

