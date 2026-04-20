from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import INDEX_PATH, SOURCE_DIR
from app.models import Chunk, Document, SearchResult


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_snippet(text: str, max_length: int = 240) -> str:
    normalized = normalize_whitespace(text)
    if len(normalized) <= max_length:
        return normalized
    return textwrap.shorten(normalized, width=max_length, placeholder="...")


def parse_markdown_document(path: Path) -> Document:
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    metadata: Dict[str, str] = {}
    body_start = 0

    for index, line in enumerate(lines):
        if not line.strip():
            body_start = index + 1
            break
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()

    body = "\n".join(lines[body_start:]).strip()
    document_id = metadata.get("document-id", path.stem.upper())
    title = metadata.get("title", path.stem.replace("-", " ").title())
    category = metadata.get("category", "general")
    audience = metadata.get("audience", "support")

    return Document(
        document_id=document_id,
        title=title,
        category=category,
        audience=audience,
        path=str(path),
        text=body,
    )


def split_sections(text: str) -> List[Tuple[str, str]]:
    sections: List[Tuple[str, str]] = []
    current_heading = "Overview"
    current_lines: List[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = line[3:].strip()
            continue
        if line.startswith("# "):
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(heading, body) for heading, body in sections if body]


def build_chunks(document: Document, chunk_size: int = 520) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_index = 1

    for heading, section_text in split_sections(document.text):
        current_block: List[str] = []
        current_length = 0

        for line in section_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            projected_length = current_length + len(stripped) + 1
            if current_block and projected_length > chunk_size:
                chunk_text = "\n".join(current_block).strip()
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.document_id}-{chunk_index:02d}",
                        document_id=document.document_id,
                        title=document.title,
                        heading=heading,
                        category=document.category,
                        text=chunk_text,
                        tokens=tokenize(f"{document.title} {heading} {chunk_text}"),
                    )
                )
                chunk_index += 1
                current_block = [stripped]
                current_length = len(stripped)
                continue

            current_block.append(stripped)
            current_length = projected_length

        if current_block:
            chunk_text = "\n".join(current_block).strip()
            chunks.append(
                Chunk(
                    chunk_id=f"{document.document_id}-{chunk_index:02d}",
                    document_id=document.document_id,
                    title=document.title,
                    heading=heading,
                    category=document.category,
                    text=chunk_text,
                    tokens=tokenize(f"{document.title} {heading} {chunk_text}"),
                )
            )
            chunk_index += 1

    return chunks


class KnowledgeBase:
    def __init__(self, source_dir: Path = SOURCE_DIR, index_path: Path = INDEX_PATH) -> None:
        self.source_dir = source_dir
        self.index_path = index_path
        self.documents: List[Document] = []
        self.chunks: List[Chunk] = []

        if self.index_path.exists():
            self.load()
        else:
            self.rebuild()

    def load(self) -> None:
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.documents = [Document(**item) for item in payload.get("documents", [])]
        self.chunks = [Chunk(**item) for item in payload.get("chunks", [])]

    def rebuild(self) -> Dict[str, int]:
        self.documents = []
        self.chunks = []

        for path in sorted(self.source_dir.glob("*.md")):
            document = parse_markdown_document(path)
            self.documents.append(document)
            self.chunks.extend(build_chunks(document))

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(self.documents),
            "chunk_count": len(self.chunks),
            "documents": [document.to_dict() for document in self.documents],
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"document_count": len(self.documents), "chunk_count": len(self.chunks)}

    def list_documents(self) -> List[Dict[str, str]]:
        return [
            {
                "document_id": document.document_id,
                "title": document.title,
                "category": document.category,
                "audience": document.audience,
                "path": document.path,
            }
            for document in self.documents
        ]

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_text = query.lower()
        scored_results: List[SearchResult] = []

        for chunk in self.chunks:
            token_overlap = sum(1 for token in query_tokens if token in chunk.tokens)
            phrase_bonus = 4 if query_text in chunk.text.lower() or query_text in chunk.heading.lower() else 0
            title_overlap = sum(1 for token in query_tokens if token in tokenize(chunk.title))
            heading_overlap = sum(1 for token in query_tokens if token in tokenize(chunk.heading))
            category_bonus = 1 if chunk.category.lower() in query_text else 0

            score = float((token_overlap * 2) + phrase_bonus + title_overlap + heading_overlap + category_bonus)
            if score <= 0:
                continue

            scored_results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    heading=chunk.heading,
                    category=chunk.category,
                    score=score,
                    snippet=make_snippet(chunk.text),
                )
            )

        scored_results.sort(key=lambda item: (-item.score, item.title, item.chunk_id))
        return scored_results[:top_k]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
