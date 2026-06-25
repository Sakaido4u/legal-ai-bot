#!/usr/bin/env python3
"""Run retrieval quality benchmarks against the loaded RAG index."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backend.config import Settings  # noqa: E402
from backend.rag_service import build_engine  # noqa: E402
from ml.benchmarks import run_retrieval_benchmark  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval benchmark suite")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    settings = Settings()
    engine = build_engine(settings)
    report = run_retrieval_benchmark(engine.retriever)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Pass rate: {report['passed']}/{report['total']} ({report['pass_rate']:.0%})")
        for case in report["cases"]:
            mark = "PASS" if case["passed"] else "FAIL"
            print(
                f"  [{mark}] {case['name']}: hits={case['retrieved']} "
                f"jurisdiction={case['jurisdiction_hit']} keywords={case['keyword_hits']}"
            )


if __name__ == "__main__":
    main()
