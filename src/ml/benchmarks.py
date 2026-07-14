from __future__ import annotations

from dataclasses import dataclass

from .llm_backend import LLMProvider, generate_with_llm
from .llm_citations import citation_quality_metrics, passages_to_citations, validate_citation_answer
from .retriever import HighPrecisionRetriever
from .schemas import Citation, Jurisdiction


@dataclass
class BenchmarkCase:
    name: str
    query: str
    product_feature: str
    jurisdictions: list[Jurisdiction]
    expect_jurisdiction: Jurisdiction
    expect_keywords: list[str]
    min_hits: int = 1
    expect_refusal: bool = False


DEFAULT_BENCHMARKS: list[BenchmarkCase] = [
    BenchmarkCase(
        name="gdpr_special_categories",
        query="Can we process biometric health data without explicit consent?",
        product_feature="Biometric health data collection",
        jurisdictions=[Jurisdiction.GDPR],
        expect_jurisdiction=Jurisdiction.GDPR,
        expect_keywords=["prohibited", "consent", "biometric", "health", "special", "processing"],
    ),
    BenchmarkCase(
        name="dpdp_children_consent",
        query="What consent is required to process personal data of children?",
        product_feature="Child user registration",
        jurisdictions=[Jurisdiction.DPDP],
        expect_jurisdiction=Jurisdiction.DPDP,
        expect_keywords=["child", "consent", "verifiable", "parent", "guardian"],
    ),
    BenchmarkCase(
        name="ccpa_sensitive_limit",
        query="Can consumers limit use of sensitive personal information like geolocation?",
        product_feature="Location tracking",
        jurisdictions=[Jurisdiction.CCPA],
        expect_jurisdiction=Jurisdiction.CCPA,
        expect_keywords=["sensitive", "limit", "geolocation", "personal", "information"],
    ),
    BenchmarkCase(
        name="cross_jurisdiction_erasure",
        query="What are user rights to delete or erase personal data?",
        product_feature="Account deletion",
        jurisdictions=[Jurisdiction.GDPR, Jurisdiction.DPDP, Jurisdiction.CCPA],
        expect_jurisdiction=Jurisdiction.GDPR,
        expect_keywords=["erasure", "delete", "right", "data"],
        min_hits=1,
    ),
    BenchmarkCase(
        name="gdpr_automated_decisions",
        query="What rules apply to automated decision-making and profiling?",
        product_feature="AI-based credit scoring",
        jurisdictions=[Jurisdiction.GDPR],
        expect_jurisdiction=Jurisdiction.GDPR,
        expect_keywords=["automated", "decision", "profiling", "right"],
    ),
    BenchmarkCase(
        name="dpdp_data_fiduciary_obligations",
        query="What are the obligations of a data fiduciary under DPDP?",
        product_feature="User data platform",
        jurisdictions=[Jurisdiction.DPDP],
        expect_jurisdiction=Jurisdiction.DPDP,
        expect_keywords=["fiduciary", "data", "oblig", "personal"],
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


def run_answer_benchmark(
    retriever: HighPrecisionRetriever,
    *,
    provider: LLMProvider = "template",
    model: str = "compliance-llm",
    api_key: str | None = None,
    ollama_base_url: str = "http://127.0.0.1:11434",
    openai_base_url: str = "https://api.openai.com/v1",
    timeout: float = 60.0,
    cases: list[BenchmarkCase] | None = None,
) -> dict:
    """Evaluate LLM answer quality: citation validity, coverage, and keyword grounding."""
    cases = cases or DEFAULT_BENCHMARKS
    results: list[dict] = []
    passed = 0

    for case in cases:
        hits = retriever.retrieve(case.query, case.jurisdictions, top_k=4, use_mmr=True)
        citations: list[Citation] = passages_to_citations(hits)
        allowed_ids = [c.citation_id for c in citations]

        llm = generate_with_llm(
            query=case.query,
            product_feature=case.product_feature,
            citations=citations,
            provider=provider,
            model=model,
            api_key=api_key,
            ollama_base_url=ollama_base_url,
            openai_base_url=openai_base_url,
            timeout=timeout,
        )

        if case.expect_refusal:
            ok = llm.refused_insufficient_citations
            metrics = {"expect_refusal": True}
        elif not citations:
            ok = llm.refused_insufficient_citations
            metrics = {"no_citations": True}
        else:
            metrics = citation_quality_metrics(llm.answer_text, allowed_ids)
            has_answer = bool(llm.answer_text.strip()) and not llm.refused_insufficient_citations
            citation_ok = validate_citation_answer(llm.answer_text, allowed_ids, require_per_sentence=True)
            combined = llm.answer_text.lower()
            kw_hits = sum(1 for kw in case.expect_keywords if kw.lower() in combined)
            ok = has_answer and citation_ok and kw_hits >= 1
            metrics["keyword_hits_in_answer"] = kw_hits

        if ok:
            passed += 1

        results.append(
            {
                "name": case.name,
                "passed": ok,
                "refused": llm.refused_insufficient_citations,
                "citation_ids_used": llm.citation_ids_used,
                **metrics,
            }
        )

    return {
        "total": len(cases),
        "passed": passed,
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "provider": provider,
        "cases": results,
    }


def run_full_benchmark(
    retriever: HighPrecisionRetriever,
    *,
    provider: LLMProvider = "template",
    model: str = "compliance-llm",
    api_key: str | None = None,
    ollama_base_url: str = "http://127.0.0.1:11434",
    openai_base_url: str = "https://api.openai.com/v1",
    timeout: float = 60.0,
    cases: list[BenchmarkCase] | None = None,
) -> dict:
    """Run retrieval + answer quality benchmarks together."""
    cases = cases or DEFAULT_BENCHMARKS
    retrieval = run_retrieval_benchmark(retriever, cases)
    answer = run_answer_benchmark(
        retriever,
        provider=provider,
        model=model,
        api_key=api_key,
        ollama_base_url=ollama_base_url,
        openai_base_url=openai_base_url,
        timeout=timeout,
        cases=cases,
    )
    combined_passed = sum(1 for r, a in zip(retrieval["cases"], answer["cases"]) if r["passed"] and a["passed"])
    return {
        "retrieval": retrieval,
        "answer": answer,
        "combined_pass_rate": round(combined_passed / len(cases), 4) if cases else 0.0,
        "combined_passed": combined_passed,
        "total_cases": len(cases),
    }
