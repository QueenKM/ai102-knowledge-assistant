from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from app.config import (
    AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_MODEL,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_CHAT_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_INDEX_NAME,
)
from app.config import SOURCE_DIR
from app.knowledge_base import KnowledgeBase, make_snippet
from app.models import AnswerResponse, Citation, Chunk, SearchResult
from app.safety import check_prompt, redact_sensitive_info


class AzureConfigurationError(RuntimeError):
    """Raised when the optional Azure runtime is not configured correctly."""


@dataclass
class AzureSettings:
    openai_endpoint: str = AZURE_OPENAI_ENDPOINT
    openai_api_key: str = AZURE_OPENAI_API_KEY
    openai_chat_deployment: str = AZURE_OPENAI_CHAT_DEPLOYMENT
    search_endpoint: str = AZURE_SEARCH_ENDPOINT
    search_api_key: str = AZURE_SEARCH_API_KEY
    search_index_name: str = AZURE_SEARCH_INDEX_NAME
    document_intelligence_endpoint: str = AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    document_intelligence_api_key: str = AZURE_DOCUMENT_INTELLIGENCE_API_KEY
    document_intelligence_model: str = AZURE_DOCUMENT_INTELLIGENCE_MODEL

    def missing_runtime_settings(self) -> List[str]:
        missing: List[str] = []
        required = {
            "AZURE_OPENAI_ENDPOINT": self.openai_endpoint,
            "AZURE_OPENAI_API_KEY": self.openai_api_key,
            "AZURE_OPENAI_CHAT_DEPLOYMENT": self.openai_chat_deployment,
            "AZURE_SEARCH_ENDPOINT": self.search_endpoint,
            "AZURE_SEARCH_API_KEY": self.search_api_key,
            "AZURE_SEARCH_INDEX_NAME": self.search_index_name,
        }
        for key, value in required.items():
            if not value:
                missing.append(key)
        return missing

    def missing_document_intelligence_settings(self) -> List[str]:
        missing: List[str] = []
        required = {
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": self.document_intelligence_endpoint,
            "AZURE_DOCUMENT_INTELLIGENCE_API_KEY": self.document_intelligence_api_key,
        }
        for key, value in required.items():
            if not value:
                missing.append(key)
        return missing


def _require_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise AzureConfigurationError(
            "The 'openai' package is required for Azure mode. Install requirements-azure.txt first."
        ) from exc
    return OpenAI


def _require_search_clients():
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import SearchField, SearchFieldDataType, SearchIndex
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise AzureConfigurationError(
            "The Azure AI Search SDK is required for Azure mode. Install requirements-azure.txt first."
        ) from exc
    return AzureKeyCredential, SearchClient, SearchIndexClient, SearchField, SearchFieldDataType, SearchIndex


def _require_document_intelligence_client():
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise AzureConfigurationError(
            "The Azure AI Document Intelligence SDK is required for document import."
        ) from exc
    return DocumentIntelligenceClient, AzureKeyCredential


class AzureSearchStore:
    def __init__(self, settings: AzureSettings) -> None:
        self.settings = settings
        (
            azure_key_credential,
            search_client_cls,
            search_index_client_cls,
            search_field_cls,
            search_field_data_type,
            search_index_cls,
        ) = _require_search_clients()
        self._search_field_cls = search_field_cls
        self._search_field_data_type = search_field_data_type
        self._search_index_cls = search_index_cls
        credential = azure_key_credential(self.settings.search_api_key)
        self.search_client = search_client_cls(
            endpoint=self.settings.search_endpoint,
            index_name=self.settings.search_index_name,
            credential=credential,
        )
        self.index_client = search_index_client_cls(
            endpoint=self.settings.search_endpoint,
            credential=credential,
        )

    def create_or_update_index(self) -> Dict[str, str]:
        search_field = self._search_field_cls
        field_type = self._search_field_data_type
        search_index = self._search_index_cls

        fields = [
            search_field(name="id", type=field_type.String, key=True, filterable=True, sortable=True),
            search_field(name="document_id", type=field_type.String, filterable=True, sortable=True),
            search_field(name="title", type=field_type.String, searchable=True, sortable=True),
            search_field(name="heading", type=field_type.String, searchable=True, sortable=True),
            search_field(name="category", type=field_type.String, searchable=True, filterable=True, facetable=True),
            search_field(name="content", type=field_type.String, searchable=True),
            search_field(name="source_path", type=field_type.String, filterable=True),
        ]

        index = search_index(name=self.settings.search_index_name, fields=fields)
        self.index_client.create_or_update_index(index)
        return {"search_index_name": self.settings.search_index_name}

    def upload_chunks(self, chunks: Sequence[Chunk]) -> Dict[str, int]:
        documents = [
            {
                "id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "heading": chunk.heading,
                "category": chunk.category,
                "content": chunk.text,
                "source_path": chunk.document_id,
            }
            for chunk in chunks
        ]
        results = self.search_client.upload_documents(documents=documents)
        succeeded = sum(1 for item in results if getattr(item, "succeeded", False))
        return {"uploaded_document_count": succeeded, "attempted_document_count": len(documents)}

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        if not query.strip():
            return []

        results = self.search_client.search(
            search_text=query,
            search_fields=["title", "heading", "category", "content"],
            select=["id", "document_id", "title", "heading", "category", "content", "source_path"],
            top=top_k,
        )

        search_results: List[SearchResult] = []
        for item in results:
            row = dict(item)
            search_results.append(
                SearchResult(
                    chunk_id=str(row.get("id", "")),
                    document_id=str(row.get("document_id", "")),
                    title=str(row.get("title", "")),
                    heading=str(row.get("heading", "")),
                    category=str(row.get("category", "")),
                    score=float(row.get("@search.score", 0.0)),
                    snippet=make_snippet(str(row.get("content", ""))),
                )
            )

        return search_results

    def list_documents(self, top: int = 25) -> List[Dict[str, str]]:
        results = self.search_client.search(
            search_text="*",
            select=["document_id", "title", "category", "source_path"],
            top=top,
        )

        unique_documents: Dict[str, Dict[str, str]] = {}
        for item in results:
            row = dict(item)
            document_id = str(row.get("document_id", ""))
            if document_id in unique_documents:
                continue
            unique_documents[document_id] = {
                "document_id": document_id,
                "title": str(row.get("title", "")),
                "category": str(row.get("category", "")),
                "audience": "azure-index",
                "path": str(row.get("source_path", "")),
            }
        return list(unique_documents.values())

    def get_document_count(self) -> int:
        return int(self.search_client.get_document_count())


class AzureOpenAIKnowledgeAssistant:
    def __init__(self, search_store: AzureSearchStore, settings: AzureSettings) -> None:
        self.search_store = search_store
        self.settings = settings
        openai_cls = _require_openai_client()
        base_url = self.settings.openai_endpoint.rstrip("/") + "/openai/v1/"
        self.client = openai_cls(
            api_key=self.settings.openai_api_key,
            base_url=base_url,
        )

    def ask(self, question: str, top_k: int = 3) -> AnswerResponse:
        allowed, reason = check_prompt(question)
        if not allowed:
            return AnswerResponse(
                answer="This request is blocked by the assistant safety policy.",
                citations=[],
                safety_allowed=False,
                safety_reason=reason,
            )

        results = self.search_store.search(question, top_k=top_k)
        if not results:
            return AnswerResponse(
                answer=(
                    "I could not find grounded guidance for that request in the Azure AI Search index. "
                    "Try a more specific product, policy, or error code question."
                ),
                citations=[],
                safety_allowed=True,
            )

        citations = [
            Citation(chunk_id=result.chunk_id, title=result.title, snippet=redact_sensitive_info(result.snippet))
            for result in results
        ]

        try:
            answer = self._generate_grounded_answer(question, results)
        except Exception as exc:  # pragma: no cover - depends on external services
            answer = self._fallback_answer(question, results, str(exc))

        return AnswerResponse(
            answer=redact_sensitive_info(answer),
            citations=citations,
            safety_allowed=True,
        )

    def _generate_grounded_answer(self, question: str, results: Sequence[SearchResult]) -> str:
        context = []
        for result in results:
            context.append(
                "\n".join(
                    [
                        f"Chunk ID: {result.chunk_id}",
                        f"Title: {result.title}",
                        f"Heading: {result.heading}",
                        f"Category: {result.category}",
                        f"Snippet: {result.snippet}",
                    ]
                )
            )

        response = self.client.chat.completions.create(
            model=self.settings.openai_chat_deployment,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded product support assistant. "
                        "Answer only from the retrieved context. "
                        "If the context is insufficient, say so. "
                        "Include inline chunk references like [DOC-001-01]."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        "Retrieved context:\n"
                        + "\n\n".join(context)
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or ""
        return content.strip() or self._fallback_answer(question, results, "Empty Azure OpenAI response.")

    @staticmethod
    def _fallback_answer(question: str, results: Sequence[SearchResult], error_message: str) -> str:
        best = results[0]
        related = ", ".join(result.chunk_id for result in results[1:]) or "none"
        return (
            "Azure OpenAI generation was unavailable, so this is a retrieval-only summary.\n\n"
            f"Question: {question}\n"
            f"Best match: {best.title} / {best.heading} [{best.chunk_id}]\n"
            f"Grounded summary: {best.snippet}\n"
            f"Related chunks: {related}\n"
            f"Generation error: {error_message}"
        )


class AzureDocumentIntelligenceIngestor:
    def __init__(self, settings: AzureSettings) -> None:
        missing = settings.missing_document_intelligence_settings()
        if missing:
            raise AzureConfigurationError(
                "Document Intelligence is not configured. Missing: " + ", ".join(missing)
            )
        self.settings = settings
        document_client_cls, azure_key_credential = _require_document_intelligence_client()
        self.client = document_client_cls(
            endpoint=self.settings.document_intelligence_endpoint,
            credential=azure_key_credential(self.settings.document_intelligence_api_key),
        )

    def ingest_directory(self, input_dir: Path, output_dir: Path = SOURCE_DIR) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files: List[Path] = []

        for path in sorted(input_dir.iterdir()):
            if path.is_dir():
                continue
            written_files.append(self.ingest_file(path, output_dir))

        return written_files

    def ingest_file(self, source_path: Path, output_dir: Path = SOURCE_DIR) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        with source_path.open("rb") as handle:
            poller = self.client.begin_analyze_document(
                self.settings.document_intelligence_model,
                body=handle,
                output_content_format="markdown",
            )
            result = poller.result()

        title = source_path.stem.replace("-", " ").replace("_", " ").title()
        document_id = self._make_document_id(source_path)
        content = getattr(result, "content", "") or ""

        markdown = (
            f"Title: {title}\n"
            "Category: imported\n"
            "Audience: support\n"
            f"Document-ID: {document_id}\n"
            f"Source-File: {source_path.name}\n\n"
            f"# {title}\n\n"
            f"{content.strip()}\n"
        )

        output_path = output_dir / f"{source_path.stem}.md"
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    @staticmethod
    def _make_document_id(source_path: Path) -> str:
        normalized = re.sub(r"[^A-Z0-9]+", "-", source_path.stem.upper()).strip("-")
        return f"DI-{normalized or 'DOCUMENT'}"


def sync_local_chunks_to_azure_search(
    knowledge_base: KnowledgeBase,
    settings: AzureSettings,
    rebuild_local_index: bool = False,
) -> Dict[str, int]:
    if rebuild_local_index:
        knowledge_base.rebuild()

    search_store = AzureSearchStore(settings)
    search_store.create_or_update_index()
    upload_stats = search_store.upload_chunks(knowledge_base.chunks)
    return {
        "document_count": len(knowledge_base.documents),
        "chunk_count": len(knowledge_base.chunks),
        **upload_stats,
    }

