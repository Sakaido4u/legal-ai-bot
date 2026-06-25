#!/usr/bin/env python3
"""Demo: run one compliance analysis and print formatted output."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backend.config import Settings  # noqa: E402
from backend.rag_service import build_engine, run_compliance_analysis  # noqa: E402
from ml.schemas import Jurisdiction  # noqa: E402


def main() -> None:
    settings = Settings()
    engine = build_engine(settings)
    result = run_compliance_analysis(
        engine,
        query="What consent is required to process children's personal data?",
        product_feature="Mobile app signup for users aged 13-17 with parental email verification",
        jurisdictions=[Jurisdiction.GDPR, Jurisdiction.DPDP, Jurisdiction.CCPA],
    )
    print("=" * 72)
    print("COMPLIANCE ANALYZE DEMO")
    print("=" * 72)
    print(f"Index vectors : {result['meta']['index_total_vectors']}")
    print(f"LLM provider  : {settings.llm_provider} / {settings.llm_model}")
    print()
    print("--- LLM Answer (citation-bound) ---")
    llm = result["llm"]
    if llm.get("refused_insufficient_citations"):
        print("(refused — insufficient grounded citations)")
    else:
        print(llm.get("answer_text", ""))
    print()
    print(f"Citations used: {llm.get('citation_ids_used', [])}")
    print()
    print("--- Cross-jurisdiction ---")
    for j, comp in result["cross_jurisdiction"]["by_jurisdiction"].items():
        print(f"  {j}: {comp['stance']} (confidence {comp['confidence']:.2f})")
    if result["cross_jurisdiction"].get("divergence_summary"):
        print(f"  >> {result['cross_jurisdiction']['divergence_summary']}")
    print()
    print("--- Top citations ---")
    for c in result["citations"][:3]:
        print(f"  [{c['citation_id']}] {c['jurisdiction']} — {c['source_label'][:60]}")
        print(f"       sim={c['similarity']:.3f} | {c['excerpt'][:120]}...")
    print()
    print("Full JSON saved to demo_output.json")
    (ROOT / "demo_output.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
