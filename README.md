# AI-102 Knowledge Assistant

## Goal

Build a standalone AI-102 style project that ingests support documents, creates a searchable knowledge base, and answers user questions with grounded citations and basic safety guardrails.

## Why This Project Matters

This project is designed to be interview-ready for an `AI-102` certified profile. It demonstrates the architecture and delivery pattern behind an Azure AI solution even when running locally:

- document ingestion and chunking
- search over indexed content
- grounded answers with citations
- prompt safety filtering
- a lightweight web UI for demos

## Scenario

`Nimbus Home` is a fictional appliance brand with support manuals, warranty rules, and escalation guidance. Support teams need a fast way to ask questions like:

- How do I reconnect the smart oven to Wi-Fi?
- What does error `E12` mean on the coffee machine?
- When is a customer eligible for a refund?
- When should a case be escalated to premium support?

## Local MVP Features

- zero-dependency local runtime using Python standard library only
- markdown document ingestion from `data/source_documents`
- generated local index in `data/generated/index.json`
- ranked keyword and phrase search
- grounded answer generation using top search hits
- citations with source snippets
- basic unsafe prompt blocking
- simple redaction of emails and phone numbers in answers

## Azure Upgrade Features

- optional `azure` runtime mode controlled by `KNOWLEDGE_ASSISTANT_MODE`
- `Azure AI Document Intelligence` import script for `PDF` and image files
- `Azure AI Search` index bootstrap and chunk upload
- `Azure OpenAI` answer generation over retrieved search hits
- graceful fallback to `local` mode when Azure settings are missing

## AI-102 Mapping

| Local Component | Azure AI Equivalent |
| --- | --- |
| Markdown ingestion and chunking | `Azure AI Document Intelligence` extraction pipeline |
| Local JSON index | `Azure AI Search` index |
| Deterministic answer composer | `Azure OpenAI` grounded generation |
| Prompt safety rules | `Azure AI Content Safety` or app-side guardrails |
| Local web app | `App Service`, `Container Apps`, or `Functions` hosted API |

See [Architecture Notes](docs/architecture.md) for the full mapping.

## Quick Start

Start the local web app:

```bash
cd /Users/kris/Desktop/ai102-knowledge-assistant
python3 -m app.server
```

Open:

```text
http://127.0.0.1:8080
```

The default mode is `local`. The app also reads a local `.env` file automatically if you create one.

Rebuild the local index manually:

```bash
python3 scripts/rebuild_index.py
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Azure Mode

Install the optional cloud dependencies:

```bash
python3 -m pip install -r requirements-azure.txt
```

Create a `.env` file from [.env.example](.env.example) and set:

- `KNOWLEDGE_ASSISTANT_MODE=azure`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

If you also want OCR and layout extraction from `PDF` or images, set:

- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_API_KEY`

Import raw files with Document Intelligence:

```bash
python3 scripts/import_with_document_intelligence.py --input-dir data/raw_documents
```

Create or update the Azure AI Search index and upload the local chunks:

```bash
python3 scripts/sync_to_azure_search.py --rebuild
```

Then start the app:

```bash
python3 -m app.server
```

In `azure` mode, the API keeps the same routes, but search and answer generation run against Azure services when configuration is valid.

## Suggested Demo Questions

- How do I pair the oven with Wi-Fi?
- What should I do when the BrewMaster Mini shows `E12`?
- How long is the warranty period?
- When do I escalate a premium support case?

## Project Structure

- [Web Server](app/server.py)
- [Knowledge Base](app/knowledge_base.py)
- [Azure Integration](app/azure_integration.py)
- [Runtime Selector](app/runtime.py)
- [Assistant Logic](app/assistant.py)
- [Safety Rules](app/safety.py)
- [Source Documents](data/source_documents)
- [Raw Input Folder](data/raw_documents/README.md)
- [Architecture Notes](docs/architecture.md)
- [Azure Setup Guide](docs/azure-setup.md)
- [Demo Script](docs/demo-script.md)

## Optional Azure Upgrade Path

This upgrade path is now partially implemented in code:

1. Import `PDF` or image files with `Azure AI Document Intelligence`.
2. Push chunks and metadata into `Azure AI Search`.
3. Switch answer generation to `Azure OpenAI`.
4. Add `Content Safety`, telemetry, and authentication for production.

See [.env.example](.env.example) and [docs/azure-setup.md](docs/azure-setup.md) for the exact wiring steps.
