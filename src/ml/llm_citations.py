from __future__ import annotations

import re
from typing import Iterable

from .schemas import Citation, LLMComplianceAnswer, RetrievedPassage


_CIT_REF = re.compile(r"\[((?:C)\d+)\]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


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


def extract_citation_ids(answer_text: str) -> set[str]:
    return set(_CIT_REF.findall(answer_text))


def validate_citation_coverage(answer_text: str, allowed_ids: Iterable[str]) -> bool:
    """Every [C#] in the answer must be in the allowed id set."""
    allowed = set(allowed_ids)
    refs = extract_citation_ids(answer_text)
    return refs <= allowed if refs else False


def validate_per_sentence_citations(answer_text: str, allowed_ids: Iterable[str]) -> bool:
    """
    Stricter guardrail: each substantive sentence must contain at least one [C#]
    from the allowed set. Skips empty lines and bullet markers without content.
    """
    allowed = set(allowed_ids)
    if not allowed:
        return False

    lines = [ln.strip() for ln in answer_text.splitlines() if ln.strip()]
    substantive: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
        if len(cleaned) < 12:
            continue
        if cleaned.lower().startswith(("query focus:", "product feature:", "evidence-linked")):
            continue
        substantive.append(cleaned)

    if not substantive:
        return False

    for sentence in substantive:
        for part in _SENTENCE_SPLIT.split(sentence):
            part = part.strip()
            if len(part) < 12:
                continue
            refs = extract_citation_ids(part)
            if not refs or not refs <= allowed:
                return False
    return True


def citation_quality_metrics(answer_text: str, allowed_ids: Iterable[str]) -> dict[str, float | int | bool]:
    """Compute citation precision/recall for benchmark evaluation."""
    allowed = set(allowed_ids)
    used = extract_citation_ids(answer_text)
    if not used:
        return {
            "citation_precision": 0.0,
            "citation_recall": 0.0,
            "valid_ids_only": False,
            "per_sentence_ok": False,
            "citations_used": 0,
        }
    valid = used <= allowed
    precision = 1.0 if valid else len(used & allowed) / len(used)
    recall = len(used & allowed) / len(allowed) if allowed else 0.0
    return {
        "citation_precision": round(precision, 4),
        "citation_recall": round(recall, 4),
        "valid_ids_only": valid,
        "per_sentence_ok": validate_per_sentence_citations(answer_text, allowed),
        "citations_used": len(used),
    }


def validate_citation_answer(
    answer_text: str,
    allowed_ids: Iterable[str],
    *,
    require_per_sentence: bool = True,
) -> bool:
    """Combined citation validation: valid IDs + optional per-sentence coverage."""
    if not answer_text.strip():
        return False
    if not validate_citation_coverage(answer_text, allowed_ids):
        return False
    if require_per_sentence and not validate_per_sentence_citations(answer_text, allowed_ids):
        return False
    return True
