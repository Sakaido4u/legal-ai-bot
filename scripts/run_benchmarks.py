#!/usr/bin/env python3
"""Run retrieval and answer quality benchmarks against the loaded RAG index."""

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
from ml.benchmarks import run_answer_benchmark, run_full_benchmark, run_retrieval_benchmark  # noqa: E402
from ml.llm_backend import resolve_llm_provider  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval + answer quality benchmark suite")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument(
        "--mode",
        choices=["retrieval", "answer", "full"],
        default="full",
        help="Benchmark mode (default: full)",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=None,
        help="Exit 1 if pass rate is below this threshold (0.0–1.0)",
    )
    args = parser.parse_args()

    settings = Settings()
    engine = build_engine(settings)
    provider = resolve_llm_provider(
        settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        llm_model=settings.llm_model,
    )

    if args.mode == "retrieval":
        report = run_retrieval_benchmark(engine.retriever)
    elif args.mode == "answer":
        report = run_answer_benchmark(
            engine.retriever,
            provider=provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            ollama_base_url=settings.ollama_base_url,
            openai_base_url=settings.openai_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    else:
        report = run_full_benchmark(
            engine.retriever,
            provider=provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            ollama_base_url=settings.ollama_base_url,
            openai_base_url=settings.openai_base_url,
            timeout=settings.llm_timeout_seconds,
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if args.mode == "full":
            r = report["retrieval"]
            a = report["answer"]
            print(f"Retrieval: {r['passed']}/{r['total']} ({r['pass_rate']:.0%})")
            print(f"Answer:    {a['passed']}/{a['total']} ({a['pass_rate']:.0%}) [{a['provider']}]")
            print(f"Combined:  {report['combined_passed']}/{report['total_cases']} ({report['combined_pass_rate']:.0%})")
            for rc, ac in zip(r["cases"], a["cases"]):
                rmark = "PASS" if rc["passed"] else "FAIL"
                amark = "PASS" if ac["passed"] else "FAIL"
                print(f"  [{rmark}/{amark}] {rc['name']}")
        else:
            print(f"Pass rate: {report['passed']}/{report['total']} ({report['pass_rate']:.0%})")
            for case in report["cases"]:
                mark = "PASS" if case["passed"] else "FAIL"
                print(f"  [{mark}] {case['name']}")

    if args.min_pass_rate is not None:
        rate = report["pass_rate"] if args.mode != "full" else report["combined_pass_rate"]
        if rate < args.min_pass_rate:
            sys.exit(1)


if __name__ == "__main__":
    main()
