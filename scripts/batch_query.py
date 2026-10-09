#!/usr/bin/env python3
"""
Run many compliance queries in one go and keep only relevant retrievals.

Reads queries from a .txt (one per line, '#' comments allowed) or .json file
(a list of strings, a list of {"query": ...} objects, or {"queries": [...]}),
runs each through ``services.query_service.run_legal_query`` and writes:

  outputs/results.csv        hits above the threshold (one row per chunk)
  outputs/results_all.csv    every retrieved chunk, with an above_threshold column
  outputs/query_summary.csv  one row per query (hit count, top/avg score)
  outputs/results.json       run metadata + per-query answers and hits

Scores are cosine similarities mapped to 0-1 (see services/batch_service.py).

Usage (PowerShell, from the repo root):
  $env:PYTHONPATH="src"
  python scripts/batch_query.py --queries queries.txt
  python scripts/batch_query.py --queries queries.txt --threshold 0.6 --llm-provider template
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Settings() requires a JWT secret even though this script never issues tokens.
os.environ.setdefault("COMPLIANCE_JWT_SECRET", "batch-script-local-only-" + "0" * 40)

from backend.config import Settings  # noqa: E402
from backend.rag_service import build_engine  # noqa: E402
from ml.schemas import Jurisdiction  # noqa: E402
from services.batch_service import DEFAULT_THRESHOLD, SCORE_MODES, run_batch_queries  # noqa: E402

CSV_COLUMNS = [
    "query",
    "rank",
    "citation_id",
    "chunk_id",
    "section",
    "document",
    "jurisdiction",
    "cosine",
    "score",
    "above_threshold",
    "risk_level",
    "risk_score",
    "excerpt",
    "answer_snippet",
]
SUMMARY_COLUMNS = [
    "query",
    "retrieved_count",
    "hit_count",
    "top_score",
    "avg_score",
    "response_time",
    "error",
]


def load_queries(path: Path) -> list[str]:
    if not path.is_file():
        raise SystemExit(f"Query file not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("queries", [])
        queries = [item["query"] if isinstance(item, dict) else str(item) for item in data]
    else:
        queries = [line for line in text.splitlines() if not line.strip().startswith("#")]
    queries = [q.strip() for q in queries if q and q.strip()]
    if not queries:
        raise SystemExit(f"No queries found in {path}")
    return queries


def open_db_session(use_db: bool):
    """Real PostgreSQL (logs to analysis history) or a throwaway in-memory SQLite DB."""
    if use_db:
        from database.session import SessionLocal

        return SessionLocal()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import database.models  # noqa: F401  (registers tables)
    from database.base import Base

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    # utf-8-sig so Excel shows accented characters correctly.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch compliance queries with a relevance threshold.")
    p.add_argument("--queries", type=Path, default=ROOT / "queries.txt", help="queries .txt or .json file")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs", help="output folder")
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"keep results with 0-1 score strictly above this (default {DEFAULT_THRESHOLD})",
    )
    p.add_argument(
        "--score-mode",
        choices=SCORE_MODES,
        default="clip",
        help="cosine->0-1 mapping: clip=max(0,cos) (default), shift=(cos+1)/2",
    )
    p.add_argument(
        "--jurisdictions",
        nargs="+",
        default=[j.value for j in Jurisdiction],
        choices=[j.value for j in Jurisdiction],
        help="jurisdictions to search (default: all)",
    )
    p.add_argument("--top-k", type=int, default=None, help="chunks retrieved per query (default from settings)")
    p.add_argument("--product-feature", default="General compliance review")
    p.add_argument(
        "--llm-provider",
        choices=["ollama", "openai", "template"],
        default=None,
        help="override COMPLIANCE_LLM_PROVIDER (template = fast, no LLM server needed)",
    )
    p.add_argument(
        "--use-db",
        action="store_true",
        help="log each query to the real PostgreSQL DB (default: temporary in-memory DB)",
    )
    args = p.parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        p.error("--threshold must be between 0 and 1")
    return args


def main() -> None:
    args = parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    queries = load_queries(args.queries)
    settings = Settings()
    if args.llm_provider:
        settings.llm_provider = args.llm_provider

    print(f"Loading embedding model and index ({settings.embedding_model}) ...")
    engine = build_engine(settings)
    if engine.store.is_empty():
        raise SystemExit(
            "Vector index is empty. Build it with scripts/build_corpus_index.py "
            "or set $env:COMPLIANCE_USE_DEMO_INDEX='true'."
        )
    print(f"Index vectors: {engine.store.ntotal()} | queries: {len(queries)} | "
          f"threshold: {args.threshold} ({args.score_mode})")

    def progress(i: int, n: int, s: dict) -> None:
        status = f"ERROR {s['error']}" if s["error"] else (
            f"{s['hit_count']}/{s['retrieved_count']} above threshold"
            + (f", top={s['top_score']:.3f}" if s["top_score"] is not None else "")
        )
        print(f"[{i}/{n}] {s['query'][:70]} -> {status}")

    db = open_db_session(args.use_db)
    try:
        summaries = run_batch_queries(
            db,
            engine,
            queries,
            threshold=args.threshold,
            score_mode=args.score_mode,
            product_feature=args.product_feature,
            jurisdictions=[Jurisdiction(j) for j in args.jurisdictions],
            top_k=args.top_k,
            on_progress=progress,
        )
    finally:
        db.close()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    hit_rows = [r for s in summaries for r in s["hits"]]
    all_rows = [r for s in summaries for r in s["retrieved"]]

    write_csv(out_dir / "results.csv", hit_rows, CSV_COLUMNS)
    write_csv(out_dir / "results_all.csv", all_rows, CSV_COLUMNS)
    write_csv(out_dir / "query_summary.csv", summaries, SUMMARY_COLUMNS)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "threshold": args.threshold,
        "score_mode": args.score_mode,
        "score_definition": (
            "cosine similarity (FAISS IndexFlatIP on L2-normalized embeddings) mapped to 0-1 via "
            + ("max(0, cos)" if args.score_mode == "clip" else "(cos + 1) / 2")
            + "; hit = score > threshold"
        ),
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "jurisdictions": args.jurisdictions,
        "top_k": args.top_k or settings.retrieval_top_k,
        "retriever_min_cosine": settings.min_retrieval_score,
        "index_total_vectors": engine.store.ntotal(),
        "queries": [{k: v for k, v in s.items() if k != "retrieved"} for s in summaries],
    }
    (out_dir / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"Hits above threshold: {len(hit_rows)} of {len(all_rows)} retrieved chunks")
    for name in ("results.csv", "results_all.csv", "query_summary.csv", "results.json"):
        print(f"  wrote {out_dir / name}")
    failed = [s for s in summaries if s["error"]]
    if failed:
        print(f"WARNING: {len(failed)} query(ies) failed; see the 'error' column in query_summary.csv")


if __name__ == "__main__":
    main()
