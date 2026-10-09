"""Map every indexed chunk to the statutory unit (GDPR Article / DPDP Section) it
was cut from, using *document position* rather than the parser's heading field.

The parser's heading field is unreliable (cross-references such as "Article 16
TFEU" in the recitals or "Article 17(2)" inside Article 58 are picked up as
headings), so article-level relevance judgments must not rely on it.  This
script also quantifies that heading error, which is reported in the paper.
"""

from __future__ import annotations

import collections
import json

from common import (
    INDEX_DIR,
    PDFS,
    RESULTS,
    NormalizedDoc,
    dpdp_section_boundaries,
    dump_json,
    gdpr_article_boundaries,
    label_at,
    labels_spanning,
    load_meta,
    load_pdf_text,
    locate,
    norm,
)

# CCPA has 7 chunks from an OAG overview page; label them by hand (topic tags).
CCPA_TOPICS = {
    0: ["overview", "right_to_know", "right_to_delete", "opt_out_sale", "non_discrimination"],
    1: ["right_to_know", "right_to_delete", "opt_out_sale", "non_discrimination", "right_to_correct"],
    2: ["right_to_correct", "limit_sensitive_pi", "business_obligations", "notices"],
    3: ["topic_index"],
    4: ["faq_disclaimer"],
    5: ["non_discrimination", "financial_incentive"],
    6: ["external_resources"],
}


def build_map(index_dir, name: str) -> dict:
    docs = {}
    bounds = {}
    for j, pdf in PDFS.items():
        raw = load_pdf_text(pdf)
        nd = NormalizedDoc(raw)
        docs[j] = nd
        b = gdpr_article_boundaries(raw) if j == "GDPR" else dpdp_section_boundaries(raw)
        bounds[j] = [(nd.raw_to_norm(pos), lab) for pos, lab in b]
        print(f"[{name}] {j}: {len(b) - 1} sequential units detected (last: {b[-1][1]})")

    chunk_map: dict[str, dict] = {}
    unlocated = collections.Counter()
    heading_mismatch = collections.Counter()
    heading_total = collections.Counter()

    for j in ("GDPR", "DPDP"):
        for row in load_meta(index_dir, j):
            pos = locate(docs[j], row["text"])
            if pos is None:
                unlocated[j] += 1
                unit = "UNLOCATED"
                units = [unit]
            else:
                unit = label_at(bounds[j], pos)
                units = labels_spanning(bounds[j], pos, pos + len(norm(row["text"])))
            chunk_map[row["chunk_id"]] = {
                "jurisdiction": j,
                "unit": unit,
                "units": units,
                "heading": row.get("heading"),
            }
            heading_total[j] += 1
            h = (row.get("heading") or "").strip()
            if unit not in ("UNLOCATED",) and h != unit:
                heading_mismatch[j] += 1

    for i, row in enumerate(load_meta(index_dir, "CCPA")):
        chunk_map[row["chunk_id"]] = {
            "jurisdiction": "CCPA",
            "unit": f"CCPA chunk {i}",
            "topics": CCPA_TOPICS.get(i, []),
            "heading": row.get("heading"),
        }

    per_unit = collections.Counter(v["unit"] for v in chunk_map.values())
    stats = {
        "index_dir": str(index_dir),
        "chunks": {j: heading_total[j] for j in heading_total} | {"CCPA": 7},
        "unlocated": dict(unlocated),
        "heading_field_disagrees_with_position": {
            j: {"count": heading_mismatch[j], "of": heading_total[j], "rate": round(heading_mismatch[j] / heading_total[j], 3)}
            for j in heading_total
        },
        "recital_chunks_gdpr": per_unit.get("Recital", 0),
        "operative_units_covered": {
            "GDPR": sum(1 for u in per_unit if u.startswith("Article")),
            "DPDP": sum(1 for u in per_unit if u.startswith("Section")),
        },
        "chunks_per_unit_top": per_unit.most_common(12),
    }
    return {"chunks": chunk_map, "stats": stats}


if __name__ == "__main__":
    out = build_map(INDEX_DIR, "base")
    dump_json(out, RESULTS / "chunk_unit_map.json")
    print(json.dumps(out["stats"], indent=2))
