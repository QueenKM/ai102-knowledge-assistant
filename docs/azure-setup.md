# Azure Setup Guide

## Goal

Switch the project from the default `local` runtime to a cloud-backed `azure` runtime while preserving the same UI and API routes.

## Services Used

- `Azure OpenAI` for grounded answer generation
- `Azure AI Search` for chunk indexing and retrieval
- `Azure AI Document Intelligence` for optional extraction from `PDF` and scanned files

## 1. Install Optional Dependencies

```bash
cd /Users/kris/Desktop/ai102-knowledge-assistant
python3 -m pip install -r requirements-azure.txt
```

## 2. Configure Environment Variables

Create `.env` from `.env.example` and set:

```text
KNOWLEDGE_ASSISTANT_MODE=azure
AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_CHAT_DEPLOYMENT=<your-chat-deployment-name>
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<your-search-admin-key>
AZURE_SEARCH_INDEX_NAME=knowledge-assistant-index
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<your-docintel-resource>.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=<your-docintel-key>
AZURE_DOCUMENT_INTELLIGENCE_MODEL=prebuilt-layout
```

## 3. Optional Document Import

Put files in `data/raw_documents` and run:

```bash
python3 scripts/import_with_document_intelligence.py --input-dir data/raw_documents
```

This creates markdown files inside `data/source_documents`.

## 4. Build and Upload the Search Index

```bash
python3 scripts/sync_to_azure_search.py --rebuild
```

This command:

1. rebuilds the local chunk index
2. creates or updates the Azure AI Search schema
3. uploads the chunks to the configured search index

## 5. Start the App

```bash
python3 -m app.server
```

Check runtime status:

```bash
curl -s http://127.0.0.1:8080/api/health
```

If configuration is incomplete, the app falls back to `local` mode and explains why in the health payload.

## Useful Endpoints

- `GET /api/health`
- `GET /api/documents`
- `GET /api/search?q=error%20E12&top_k=3`
- `POST /api/ask`
- `POST /api/index/rebuild`

## Notes

- The current Azure AI Search integration uses keyword retrieval over uploaded chunks.
- The current Azure OpenAI integration grounds the answer on retrieved chunks and returns separate citations in the API response.
- For a production version, you would typically add authentication, telemetry, abuse monitoring, and stronger content safety.

