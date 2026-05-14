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
    """
    Placeholder "LLM" that never hallucinates: only summarizes using explicit citation markers.
    Swap this for a quantized HF model with constrained decoding + citation mask.
    """
    if not citations:
        return LLMComplianceAnswer(
            answer_text="",
            citation_ids_used=[],
            refused_insufficient_citations=True,
        )

    lines: list[str] = [
        f"**Query focus:** {query.strip()}",
        f"**Product feature:** {product_feature.strip()}",
        "",
        "**Evidence-linked notes (demo template - replace with HF generation):**",
    ]
    used: list[str] = []
    for c in citations[:5]:
        tag = f"[{c.citation_id}]"
        used.append(c.citation_id)
        lines.append(
            f"- {tag} ({c.jurisdiction.value} - {c.source_label}) excerpt indicates relevant "
            f"obligations or limits on processing; stance must be validated against full instruments "
            f"and your factual record."
        )

    lines.append(
        "\n*Every substantive claim above is tied to a bracketed citation id drawn from retrieval only.*"
    )
    return LLMComplianceAnswer(
        answer_text="\n".join(lines),
        citation_ids_used=used,
        refused_insufficient_citations=False,
    )


def validate_citation_coverage(answer_text: str, allowed_ids: Iterable[str]) -> bool:
    """
    Soft guardrail: every [C#] in the answer must be in the allowed id set.
    (Stricter: require at least one citation per sentence - left to model constraints.)
    """
    allowed = set(allowed_ids)
    refs = set(_CIT_REF.findall(answer_text))
    return refs <= allowed if refs else True
