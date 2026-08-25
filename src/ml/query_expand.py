from __future__ import annotations

import re


# Heuristic sub-topics for multi-aspect legal compliance queries.
_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"transfer|cross[- ]border|SCC|standard contractual|adequacy|"
            r"third country|international|servers? (?:located )?in|"
            r"outside the (?:EU|EEA)|(?:in|to) the (?:US|USA|United States)\b",
            re.I,
        ),
        "international personal data transfers safeguards SCCs adequacy",
    ),
    (
        re.compile(r"retain|retention|stor(?:e|age) limit|after account|years after", re.I),
        "personal data retention storage limitation principle",
    ),
    (
        re.compile(r"\bDPA\b|data processing agreement|processor|cloud hosting|hosting provider", re.I),
        "processor obligations data processing agreement Article 28",
    ),
    (
        re.compile(r"third[- ]party|advertis|shar(?:e|ing)|partners|disclosure", re.I),
        "third-party sharing disclosure of personal data recipients",
    ),
    (
        re.compile(r"special categor|sensitive|health|biometric|child", re.I),
        "special categories of personal data sensitive processing",
    ),
    (
        re.compile(r"lawful|legal basis|consent|legitimate interest", re.I),
        "lawfulness of processing legal basis consent",
    ),
]


def decompose_query(query: str) -> list[str]:
    """
    Expand a multi-part compliance question into focused sub-queries.

    Always includes the original query first. Adds topic-focused variants when
    the text matches known compliance themes (transfers, retention, DPA, etc.).
    """
    q = (query or "").strip()
    if not q:
        return []
    out: list[str] = [q]
    seen = {q.lower()}
    for pat, focus in _TOPIC_PATTERNS:
        if pat.search(q):
            sub = focus
            if re.search(r"\bGDPR\b", q, re.I):
                sub = f"GDPR {focus}"
            elif re.search(r"\bDPDP\b", q, re.I):
                sub = f"DPDP {focus}"
            elif re.search(r"\bCCPA\b|\bCPRA\b", q, re.I):
                sub = f"CCPA {focus}"
            key = sub.lower()
            if key not in seen:
                seen.add(key)
                out.append(sub)
    return out
