from __future__ import annotations

from typing import Dict, List

from app.assistant import KnowledgeAssistant
from app.azure_integration import (
    AzureConfigurationError,
    AzureOpenAIKnowledgeAssistant,
    AzureSearchStore,
    AzureSettings,
    sync_local_chunks_to_azure_search,
)
from app.config import REQUESTED_MODE
from app.knowledge_base import KnowledgeBase
from app.models import AnswerResponse, SearchResult


class AssistantRuntime:
    def __init__(self) -> None:
        self.requested_mode = REQUESTED_MODE if REQUESTED_MODE in {"local", "azure"} else "local"
        self.active_mode = "local"
        self.note = ""
        self.knowledge_base = KnowledgeBase()
        self.local_assistant = KnowledgeAssistant(self.knowledge_base)
        self.assistant = self.local_assistant
        self.search_store = None
        self.azure_settings = AzureSettings()

        if REQUESTED_MODE not in {"local", "azure"}:
            self.note = (
                f"Unsupported mode '{REQUESTED_MODE}'. Falling back to local mode. "
                "Use 'local' or 'azure'."
            )
            return

        if self.requested_mode == "azure":
            self._activate_azure_mode()

    def _activate_azure_mode(self) -> None:
        missing = self.azure_settings.missing_runtime_settings()
        if missing:
            self.note = (
                "Azure mode was requested but configuration is incomplete. "
                f"Missing: {', '.join(missing)}. Falling back to local mode."
            )
            return

        try:
            self.search_store = AzureSearchStore(self.azure_settings)
            self.assistant = AzureOpenAIKnowledgeAssistant(self.search_store, self.azure_settings)
            self.active_mode = "azure"
            self.note = (
                "Azure mode is active. Search runs against Azure AI Search and answers are generated with Azure OpenAI."
            )
        except AzureConfigurationError as exc:
            self.note = f"{exc} Falling back to local mode."

    def ask(self, question: str, top_k: int) -> AnswerResponse:
        try:
            return self.assistant.ask(question, top_k=top_k)
        except Exception as exc:  # pragma: no cover - depends on external services
            self.note = f"Azure request failed: {exc}. Local fallback is active for this request."
            return self.local_assistant.ask(question, top_k=top_k)

    def search(self, query: str, top_k: int) -> List[SearchResult]:
        if self.active_mode != "azure" or not self.search_store:
            return self.knowledge_base.search(query, top_k=top_k)

        try:
            return self.search_store.search(query, top_k=top_k)
        except Exception as exc:  # pragma: no cover - depends on external services
            self.note = f"Azure Search query failed: {exc}. Showing local search results instead."
            return self.knowledge_base.search(query, top_k=top_k)

    def list_documents(self) -> List[Dict[str, str]]:
        if self.active_mode != "azure" or not self.search_store:
            return self.knowledge_base.list_documents()

        try:
            documents = self.search_store.list_documents()
            return documents or self.knowledge_base.list_documents()
        except Exception as exc:  # pragma: no cover - depends on external services
            self.note = f"Azure Search listing failed: {exc}. Showing local documents instead."
            return self.knowledge_base.list_documents()

    def rebuild(self) -> Dict[str, object]:
        local_stats = self.knowledge_base.rebuild()
        payload: Dict[str, object] = {
            "mode": self.active_mode,
            "local_document_count": local_stats["document_count"],
            "local_chunk_count": local_stats["chunk_count"],
        }

        if self.active_mode == "azure":
            try:
                azure_stats = sync_local_chunks_to_azure_search(self.knowledge_base, self.azure_settings)
                payload["azure_sync"] = azure_stats
            except Exception as exc:  # pragma: no cover - depends on external services
                payload["azure_sync_error"] = str(exc)

        return payload

    def health(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "status": "ok",
            "requested_mode": self.requested_mode,
            "active_mode": self.active_mode,
            "document_count": len(self.knowledge_base.documents),
            "chunk_count": len(self.knowledge_base.chunks),
            "note": self.note,
        }

        if self.active_mode == "azure" and self.search_store:
            try:
                payload["azure_index_document_count"] = self.search_store.get_document_count()
                payload["azure_search_index_name"] = self.azure_settings.search_index_name
            except Exception as exc:  # pragma: no cover - depends on external services
                payload["azure_health_error"] = str(exc)

        return payload

