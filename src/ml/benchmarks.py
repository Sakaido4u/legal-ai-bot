from __future__ import annotations

from dataclasses import dataclass

from .retriever import HighPrecisionRetriever
from .schemas import Jurisdiction


@dataclass
class BenchmarkCase:
    name: str
    query: str
    jurisdictions: list[Jurisdiction]
    expect_jurisdiction: Jurisdiction
    expect_keywords: list[str]
    min_hits: int = 1


DEFAULT_BENCHMARKS: list[BenchmarkCase] = [
    BenchmarkCase(
        name="gdpr_special_categories",
        query="Can we process biometric health data without explicit consent?",
        jurisdictions=[Jurisdiction.GDPR],
        expect_jurisdiction=Jurisdiction.GDPR,
        expect_keywords=["prohibited", "consent", "biometric", "health"],
    ),
    BenchmarkCase(
        name="dpdp_children_consent",
        query="What consent is required to process personal data of children?",
        jurisdictions=[Jurisdiction.DPDP],
        expect_jurisdiction=Jurisdiction.DPDP,
        expect_keywords=["child", "consent", "verifiable"],
    ),
    BenchmarkCase(
        name="ccpa_sensitive_limit",
        query="Can consumers limit use of sensitive personal information like geolocation?",
        jurisdictions=[Jurisdiction.CCPA],
        expect_jurisdiction=Jurisdiction.CCPA,
        expect_keywords=["sensitive", "limit", "geolocation"],
    ),
    BenchmarkCase(
        name="cross_jurisdiction_erasure",
        query="What are user rights to delete or erase personal data?",
        jurisdictions=[Jurisdiction.GDPR, Jurisdiction.DPDP, Jurisdiction.CCPA],
        expect_jurisdiction=Jurisdiction.GDPR,
        expect_keywords=["erasure", "delete", "right"],
        min_hits=1,
    ),
]


def run_retrieval_benchmark(
    retriever: HighPrecisionRetriever,
    cases: list[BenchmarkCase] | None = None,
) -> dict:
    """Lightweight retrieval QA: jurisdiction hit rate + keyword overlap."""
    cases = cases or DEFAULT_BENCHMARKS
    results: list[dict] = []
    passed = 0

    for case in cases:
        hits = retriever.retrieve(case.query, case.jurisdictions, top_k=4, use_mmr=True)
        j_hit = any(h.jurisdiction == case.expect_jurisdiction for h in hits)
        combined = " ".join(h.text.lower() for h in hits)
        kw_hits = sum(1 for kw in case.expect_keywords if kw.lower() in combined)
        kw_ok = kw_hits >= min(2, len(case.expect_keywords))
        ok = len(hits) >= case.min_hits and j_hit and kw_ok
        if ok:
            passed += 1
        results.append(
            {
                "name": case.name,
                "passed": ok,
                "retrieved": len(hits),
                "jurisdiction_hit": j_hit,
                "keyword_hits": kw_hits,
                "top_similarity": round(hits[0].similarity, 4) if hits else 0.0,
            }
        )

    return {
        "total": len(cases),
        "passed": passed,
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "cases": results,
    }
