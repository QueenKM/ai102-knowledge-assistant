from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(PROJECT_ROOT / ".env")

SOURCE_DIR = PROJECT_ROOT / "data" / "source_documents"
RAW_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "raw_documents"
INDEX_PATH = PROJECT_ROOT / "data" / "generated" / "index.json"
STATIC_DIR = PROJECT_ROOT / "app" / "static"

REQUESTED_MODE = os.getenv("KNOWLEDGE_ASSISTANT_MODE", "local").strip().lower()
PORT = int(os.getenv("KNOWLEDGE_ASSISTANT_PORT", "8080"))
DEFAULT_TOP_K = int(os.getenv("KNOWLEDGE_ASSISTANT_TOP_K", "3"))

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
).strip()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY", "").strip()
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "knowledge-assistant-index").strip()

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip()
AZURE_DOCUMENT_INTELLIGENCE_API_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", "").strip()
AZURE_DOCUMENT_INTELLIGENCE_MODEL = os.getenv(
    "AZURE_DOCUMENT_INTELLIGENCE_MODEL",
    "prebuilt-layout",
).strip()

