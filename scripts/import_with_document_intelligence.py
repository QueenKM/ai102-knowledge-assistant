from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.azure_integration import AzureDocumentIntelligenceIngestor, AzureSettings
from app.config import RAW_DOCUMENTS_DIR, SOURCE_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Import PDFs/images into markdown using Azure AI Document Intelligence.")
    parser.add_argument(
        "--input-dir",
        default=str(RAW_DOCUMENTS_DIR),
        help="Directory containing PDF or image files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SOURCE_DIR),
        help="Directory where converted markdown files will be written.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    ingestor = AzureDocumentIntelligenceIngestor(AzureSettings())
    written_files = ingestor.ingest_directory(input_dir=input_dir, output_dir=output_dir)

    print(f"Imported {len(written_files)} file(s):")
    for path in written_files:
        print(path)


if __name__ == "__main__":
    main()

