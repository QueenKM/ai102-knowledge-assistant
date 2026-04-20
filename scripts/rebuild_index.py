from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.knowledge_base import KnowledgeBase


def main() -> None:
    knowledge_base = KnowledgeBase()
    stats = knowledge_base.rebuild()
    print(
        "Index rebuilt successfully: "
        f"{stats['document_count']} documents, {stats['chunk_count']} chunks."
    )


if __name__ == "__main__":
    main()
