from __future__ import annotations

import re
from typing import Iterable

from .schemas import Citation, LLMComplianceAnswer, RetrievedPassage


_CIT_REF = re.compile(r"\[((?:C)\d+)\]")


def passages_to_citations(passages: list[RetrievedPassage], citation_prefix: str = "C") -> list[Citation]:
    """Assign stable display ids [C0], [C1], ... aligned to retriever ordering."""
    out: list[Citation] = []
    for i, p in enumerate(passages):
        cid = f"{citation_prefix}{i}"
        excerpt = p.text.strip()
        if len(excerpt) > 1200:
            excerpt = excerpt[:1197] + "..."
        out.append(
            Citation(
                citation_id=cid,
                jurisdiction=p.jurisdiction,
                source_label=p.source_label,
                heading=p.heading,
                excerpt=excerpt,
                similarity=float(p.similarity),
            )
        )
    return out


def generate_citation_bound_answer(
    *,
    query: str,
    product_feature: str,
    citations: list[Citation],
) -> LLMComplianceAnswer:
    """Backward-compatible wrapper; defaults to template provider."""
    from .llm_backend import generate_with_llm

    return generate_with_llm(
        query=query,
        product_feature=product_feature,
        citations=citations,
        provider="template",
    )


def validate_citation_coverage(answer_text: str, allowed_ids: Iterable[str]) -> bool:
    """
    Soft guardrail: every [C#] in the answer must be in the allowed id set.
    (Stricter: require at least one citation per sentence - left to model constraints.)
    """
    allowed = set(allowed_ids)
    refs = set(_CIT_REF.findall(answer_text))
    return refs <= allowed if refs else True
