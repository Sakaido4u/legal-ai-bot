#!/usr/bin/env python3
"""
Unified ingestion CLI:
- PDFs and/or URLs -> ChunkRecord -> embed -> FAISS index
- or ingest from an existing seed JSON file
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ml.ingestion import CorpusSource, build_index_from_sources, build_index_from_seed_file  # noqa: E402
from ml.schemas import Jurisdiction  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest PDFs/URLs into vector store index")
    p.add_argument("--output", type=Path, default=ROOT / "vector_store" / "regulatory", help="Output directory")
    p.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-transformers model id",
    )

    p.add_argument("--seeds", type=Path, default=None, help="Seed JSON file (same schema as data/corpus_seeds.json)")

    p.add_argument("--url", action="append", default=[], help="URL to ingest (repeatable)")
    p.add_argument("--pdf", action="append", default=[], help="PDF path to ingest (repeatable)")
    p.add_argument(
        "--jurisdiction",
        choices=[j.value for j in Jurisdiction],
        default="GDPR",
        help="Jurisdiction for --url/--pdf inputs",
    )
    p.add_argument("--label", default=None, help="Source label for --url/--pdf inputs (defaults to the URL/path)")

    args = p.parse_args()

    if args.seeds:
        stats = build_index_from_seed_file(args.seeds, embedding_model=args.embedding_model, output_dir=args.output)
        print(f"Done: {stats['total_chunks']} chunks -> {stats['output_dir']}")
        return

    sources: list[CorpusSource] = []
    j = Jurisdiction(args.jurisdiction)

    for u in args.url:
        sources.append(CorpusSource(jurisdiction=j, source_type="url", label=args.label or u, url=u))
    for pdf in args.pdf:
        sources.append(CorpusSource(jurisdiction=j, source_type="pdf", label=args.label or pdf, path=pdf))

    if not sources:
        raise SystemExit("Nothing to ingest. Provide --seeds or at least one --url/--pdf.")

    stats = build_index_from_sources(sources, embedding_model=args.embedding_model, output_dir=args.output)
    print(f"Done: {stats['total_chunks']} chunks -> {stats['output_dir']}")
    if stats.get("errors"):
        print(f"Warnings: {len(stats['errors'])} source(s) failed — see ingest_stats.json")


if __name__ == "__main__":
    main()

