from __future__ import annotations

import logging
import re
from typing import Literal

import requests

from .llm_citations import validate_citation_answer
from .schemas import Citation, LLMComplianceAnswer

logger = logging.getLogger(__name__)

LLMProvider = Literal["template", "openai", "ollama"]

_CIT_REF = re.compile(r"\[((?:C)\d+)\]")
_MAX_REPROMPTS = 1


def _build_citation_prompt(
    *,
    query: str,
    product_feature: str,
    citations: list[Citation],
    strict: bool = False,
) -> tuple[str, str]:
    allowed = ", ".join(c.citation_id for c in citations)
    evidence_lines: list[str] = []
    for c in citations:
        excerpt = c.excerpt.replace("\n", " ").strip()
        evidence_lines.append(
            f"[{c.citation_id}] ({c.jurisdiction.value} — {c.source_label})\n{excerpt}"
        )

    system = (
        "You are a compliance research assistant. Answer ONLY using the evidence blocks below. "
        "Every factual sentence MUST end with one or more citation tags like [C0] drawn ONLY from: "
        f"{allowed}. Do not invent citations. Do not give legal advice — summarize retrieved evidence. "
        "If evidence is insufficient, reply with exactly: REFUSE"
    )
    if strict:
        system += (
            " STRICT MODE: Each bullet point must contain at least one [C#] tag. "
            "Do not write any sentence without a citation tag from the allowed list."
        )

    user = (
        f"Query: {query.strip()}\n"
        f"Product feature: {product_feature.strip()}\n\n"
        "Evidence:\n"
        + "\n\n".join(evidence_lines)
        + "\n\nWrite 3–6 bullet points. Each bullet must cite at least one [C#] tag."
    )
    return system, user


def _template_answer(
    *,
    query: str,
    product_feature: str,
    citations: list[Citation],
) -> LLMComplianceAnswer:
    lines: list[str] = [
        f"Query focus: {query.strip()}",
        f"Product feature: {product_feature.strip()}",
        "",
        "Evidence-linked summary:",
    ]
    used: list[str] = []
    for c in citations[:5]:
        tag = f"[{c.citation_id}]"
        used.append(c.citation_id)
        lines.append(
            f"- {tag} ({c.jurisdiction.value} — {c.source_label}): retrieved text suggests "
            f"relevant obligations or limits; validate against the full instrument and your facts."
        )
    return LLMComplianceAnswer(
        answer_text="\n".join(lines),
        citation_ids_used=used,
        refused_insufficient_citations=False,
    )


def _openai_chat(*, system: str, user: str, model: str, api_key: str, base_url: str, timeout: float) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return str(data["choices"][0]["message"]["content"]).strip()


def _ollama_chat(*, system: str, user: str, model: str, base_url: str, timeout: float) -> str:
    url = f"{base_url.rstrip('/')}/api/chat"
    resp = requests.post(
        url,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return str(data["message"]["content"]).strip()


def _extract_used_citations(answer_text: str) -> list[str]:
    return sorted(set(_CIT_REF.findall(answer_text)))


def _call_llm(
    *,
    provider: LLMProvider,
    system: str,
    user: str,
    model: str,
    api_key: str | None,
    openai_base_url: str,
    ollama_base_url: str,
    timeout: float,
) -> str:
    if provider == "openai":
        if not api_key:
            raise ValueError("COMPLIANCE_LLM_API_KEY required for openai provider")
        return _openai_chat(
            system=system,
            user=user,
            model=model,
            api_key=api_key,
            base_url=openai_base_url,
            timeout=timeout,
        )
    if provider == "ollama":
        return _ollama_chat(
            system=system,
            user=user,
            model=model,
            base_url=ollama_base_url,
            timeout=timeout,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def resolve_llm_provider(
    configured: str,
    *,
    ollama_base_url: str = "http://127.0.0.1:11434",
    llm_model: str = "compliance-llm",
) -> LLMProvider:
    """Pick a working provider: honor explicit config, auto-detect Ollama, else template."""
    if configured in ("openai", "ollama", "template"):
        if configured == "ollama":
            from .ollama_health import check_ollama_llm

            health = check_ollama_llm(ollama_base_url, llm_model)
            if health["status"] == "ok":
                return "ollama"
            logger.warning("Ollama unavailable (%s); falling back to template", health)
            return "template"
        return configured  # type: ignore[return-value]
    return "template"


def generate_with_llm(
    *,
    query: str,
    product_feature: str,
    citations: list[Citation],
    provider: LLMProvider = "template",
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    openai_base_url: str = "https://api.openai.com/v1",
    ollama_base_url: str = "http://127.0.0.1:11434",
    timeout: float = 60.0,
    max_reprompts: int = _MAX_REPROMPTS,
) -> LLMComplianceAnswer:
    if not citations:
        return LLMComplianceAnswer(
            answer_text="",
            citation_ids_used=[],
            refused_insufficient_citations=True,
        )

    if provider == "template":
        return _template_answer(query=query, product_feature=product_feature, citations=citations)

    allowed_ids = {c.citation_id for c in citations}
    raw = ""
    strict = False

    for attempt in range(max_reprompts + 1):
        system, user = _build_citation_prompt(
            query=query,
            product_feature=product_feature,
            citations=citations,
            strict=strict,
        )
        try:
            raw = _call_llm(
                provider=provider,
                system=system,
                user=user,
                model=model,
                api_key=api_key,
                openai_base_url=openai_base_url,
                ollama_base_url=ollama_base_url,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("LLM call failed (%s); falling back to template", exc)
            return _template_answer(query=query, product_feature=product_feature, citations=citations)

        if raw.upper().startswith("REFUSE") or not raw.strip():
            return LLMComplianceAnswer(
                answer_text="",
                citation_ids_used=[],
                refused_insufficient_citations=True,
            )

        if validate_citation_answer(raw, allowed_ids, require_per_sentence=True):
            used = _extract_used_citations(raw)
            return LLMComplianceAnswer(
                answer_text=raw,
                citation_ids_used=used,
                refused_insufficient_citations=False,
            )

        logger.warning("Citation validation failed (attempt %d); %s", attempt + 1, raw[:120])
        strict = True

    return LLMComplianceAnswer(
        answer_text="",
        citation_ids_used=[],
        refused_insufficient_citations=True,
    )
