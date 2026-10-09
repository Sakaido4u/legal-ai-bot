"""Descriptive analysis of the heuristic risk scorer over the whole index.

The scorer has no ground truth; this script characterises its behaviour
(level distribution, which lexicon factors fire, and which factor
combinations produce each level) so the paper can present it as an
unvalidated heuristic with known failure modes rather than a measured result.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from common import INDEX_DIR, RESULTS, dump_json, load_meta

from ml.risk_scorer import _OBLIGATION, _PENALTY, _PROHIBIT, _SENSITIVE, score_passage
from ml.schemas import Jurisdiction, RetrievedPassage

_WITHOUT_CONSENT = re.compile(r"\bwithout.*consent\b", re.I)
_PROHIBIT_STRICT = re.compile(r"\b(prohibited|shall not|must not|may not|not permitted|unlawful processing|ban on)\b", re.I)


def main() -> None:
    unit_map = json.loads((RESULTS / "chunk_unit_map.json").read_text(encoding="utf-8"))["chunks"]
    rows = []
    for j in Jurisdiction:
        for m in load_meta(INDEX_DIR, j.value):
            p = RetrievedPassage(chunk_id=m["chunk_id"], jurisdiction=j, source_label=m["source_label"], heading=m.get("heading"), text=m["text"], similarity=1.0)
            rs = score_passage(p)
            fired = {
                "prohibit": bool(_PROHIBIT.search(p.text)),
                "prohibit_strict_terms": bool(_PROHIBIT_STRICT.search(p.text)),
                "prohibit_via_without_consent_only": bool(_WITHOUT_CONSENT.search(p.text)) and not _PROHIBIT_STRICT.search(p.text),
                "penalty": bool(_PENALTY.search(p.text)),
                "obligation": bool(_OBLIGATION.search(p.text)),
                "sensitive": bool(_SENSITIVE.search(p.text)),
            }
            rows.append({"chunk_id": p.chunk_id, "jurisdiction": j.value, "unit": unit_map.get(p.chunk_id, {}).get("unit"), "level": rs.level.value, "score": rs.score, "factors": rs.factors, **fired})

    n = len(rows)
    by_level = Counter(r["level"] for r in rows)
    by_j_level = {j.value: dict(Counter(r["level"] for r in rows if r["jurisdiction"] == j.value)) for j in Jurisdiction}
    fire = {k: sum(1 for r in rows if r[k]) / n for k in ("prohibit", "prohibit_strict_terms", "prohibit_via_without_consent_only", "penalty", "obligation", "sensitive")}
    combos = Counter((tuple(sorted(r["factors"])), r["level"]) for r in rows)
    zero_factor = sum(1 for r in rows if not r["factors"]) / n
    high_rows = [r for r in rows if r["level"] == "high"]
    high_without_consent_only = sum(1 for r in high_rows if r["prohibit_via_without_consent_only"]) / max(1, len(high_rows))

    # Example: operative articles that a lawyer would call prohibitive but the scorer rates low/medium.
    examples = {}
    for r in rows:
        if r["unit"] in ("Article 9", "Article 22", "Article 44", "Section 9", "Section 16"):
            examples.setdefault(r["unit"], []).append({"level": r["level"], "score": round(r["score"], 2), "factors": r["factors"]})

    out = {
        "n_chunks": n,
        "level_distribution": {k: {"count": v, "share": v / n} for k, v in by_level.items()},
        "level_by_jurisdiction": by_j_level,
        "factor_fire_rate": fire,
        "zero_factor_share(compliance_score=100)": zero_factor,
        "high_level_share_relying_on_without_consent_regex": high_without_consent_only,
        "factor_combinations": [{"factors": list(f), "level": lvl, "count": c} for (f, lvl), c in combos.most_common()],
        "examples_by_unit": examples,
    }
    dump_json(out, RESULTS / "risk_analysis.json")
    print(json.dumps({k: v for k, v in out.items() if k not in ("factor_combinations", "examples_by_unit")}, indent=2))
    for e in out["factor_combinations"][:12]:
        print(e)


if __name__ == "__main__":
    main()
