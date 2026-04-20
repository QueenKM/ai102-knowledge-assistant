from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.azure_integration import AzureSettings, sync_local_chunks_to_azure_search
from app.knowledge_base import KnowledgeBase


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/update Azure AI Search index and upload chunks.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the local JSON index before upload.")
    args = parser.parse_args()

    knowledge_base = KnowledgeBase()
    stats = sync_local_chunks_to_azure_search(
        knowledge_base=knowledge_base,
        settings=AzureSettings(),
        rebuild_local_index=args.rebuild,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

