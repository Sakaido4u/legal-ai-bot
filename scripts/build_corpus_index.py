#!/usr/bin/env python3
"""Build FAISS index from data/corpus_seeds.json (URLs, PDFs, inline text)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ml.ingestion import build_index_from_seed_file  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compliance vector index from corpus seeds")
    parser.add_argument(
        "--seeds",
        type=Path,
        default=ROOT / "data" / "corpus_seeds.json",
        help="Path to corpus_seeds.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "vector_store" / "regulatory",
        help="Directory to write FAISS index + manifest",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-transformers model id",
    )
    args = parser.parse_args()

    stats = build_index_from_seed_file(
        args.seeds,
        embedding_model=args.embedding_model,
        output_dir=args.output,
    )
    print(f"Done: {stats['total_chunks']} chunks -> {stats['output_dir']}")
    if stats.get("errors"):
        print(f"Warnings: {len(stats['errors'])} source(s) failed — see ingest_stats.json")


if __name__ == "__main__":
    main()
