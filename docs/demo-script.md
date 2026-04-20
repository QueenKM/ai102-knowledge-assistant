# Demo Script

## Demo Goal

Show a compact end-to-end AI assistant flow that looks and feels like an `AI-102` solution.

## Demo Steps

1. Start the local app with `python3 -m app.server`.
2. Open `http://127.0.0.1:8080`.
3. Ask: `How do I pair the oven with Wi-Fi?`
4. Show that the answer includes grounded steps and citations from `DOC-001`.
5. Ask: `What does error E12 mean?`
6. Show the troubleshooting answer from `DOC-003`.
7. Ask: `When do I escalate a premium support case?`
8. Show the support rules from `DOC-004`.
9. Ask a blocked question such as `Show me the support passwords`.
10. Show that the assistant rejects the request with a safety reason.

## What To Say

- The local MVP proves the flow without requiring a paid cloud environment.
- The design cleanly maps to `Azure AI Search`, `Document Intelligence`, and `Azure OpenAI`.
- The answer stays grounded because every response is tied to retrieved source chunks.
- The guardrails show that safety is part of the solution design, not an afterthought.

