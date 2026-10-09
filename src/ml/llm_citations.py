from __future__ import annotations

import re
from typing import Iterable

from .schemas import Citation, LLMComplianceAnswer, RetrievedPassage
from .chunking import trim_orphaned_edges


_CIT_REF = re.compile(r"\[((?:C)\d+)\]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Tokens that end with a period but do not end a sentence: single-letter or
# numbered enumerators ("G.", "1.", "(a)."), and common legal abbreviations
# ("Art.", "Sec.", "para.", "No.", "e.g.", "i.e.").  Splitting after these
# produced citation-less fragments and spurious validation failures.
_ABBREV_END = re.compile(
    r"(?:(?<![A-Za-z])[A-Za-z]"
    r"|\b(?:No|Nos|Art|Arts|Sec|Secs|para|paras|cf|e\.g|i\.e|etc|vs|v|Reg|Dir|Ch|Cl|Sch|p|pp|approx|incl|resp)"
    r"|(?<![\w.])\d+"
    r"|\([a-z0-9]{1,3}\))\.$",
    re.I,
)


def split_validation_sentences(text: str) -> list[str]:
    """Sentence split for citation validation that does not break after abbreviations/enumerators."""
    out: list[str] = []
    for part in _SENTENCE_SPLIT.split(text):
        if out and _ABBREV_END.search(out[-1]):
            out[-1] = f"{out[-1]} {part}"
        else:
            out.append(part)
    return out


def passages_to_citations(passages: list[RetrievedPassage], citation_prefix: str = "C") -> list[Citation]:
    """Assign stable display ids [C0], [C1], ... aligned to retriever ordering."""
    out: list[Citation] = []
    for i, p in enumerate(passages):
        cid = f"{citation_prefix}{i}"
        excerpt = trim_orphaned_edges(p.text.strip())
        if len(excerpt) > 1200:
            # Prefer cutting at a sentence boundary near the limit.
            cut = excerpt[:1200]
            last = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
            excerpt = (cut[: last + 1] if last >= 400 else cut[:1197]) + ("..." if last < 400 else "")
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


def substantive_lines(answer_text: str, *, skip_list_introducers: bool = True) -> list[str]:
    """
    Lines of an answer that carry factual content and therefore need a citation.

    Skips empty lines, bullet markers without content, template scaffolding, and
    (by default) list-introducer lines such as "Here are the key points:" — a line
    that ends with a colon and carries no citation makes no standalone claim.
    Treating such preambles as uncited claims was the dominant cause of validator
    refusals in our benchmark.
    """
    out: list[str] = []
    for line in answer_text.splitlines():
        cleaned = re.sub(r"^[-*•]\s*", "", line.strip()).strip()
        if len(cleaned) < 12:
            continue
        if cleaned.lower().startswith(("query focus:", "product feature:", "evidence-linked")):
            continue
        if skip_list_introducers and cleaned.endswith(":") and not extract_citation_ids(cleaned):
            continue
        out.append(cleaned)
    return out


def validate_per_sentence_citations(answer_text: str, allowed_ids: Iterable[str]) -> bool:
    """
    Stricter guardrail: each substantive sentence must contain at least one [C#]
    from the allowed set. Skips empty lines and bullet markers without content.
    """
    allowed = set(allowed_ids)
    if not allowed:
        return False

    substantive = substantive_lines(answer_text)
    if not substantive:
        return False

    for sentence in substantive:
        for part in split_validation_sentences(sentence):
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
