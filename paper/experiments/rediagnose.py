"""Re-score logged generation attempts under several validator variants.

Lets us attribute refusals to validator rules without re-querying the LLM:
for each logged run, every attempt is re-diagnosed with the current
``diagnose`` function (legacy splitter / fixed splitter x header-skip on/off)
and the production loop outcome is re-derived for every variant that is at
least as strict as the validator used during the run.

Usage: python rediagnose.py generation_<tag>.json <validator-used-in-run>
       validator-used-in-run in {legacy, splitter_fix, header_fix, both_fixes}
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from common import RESULTS, dump_json
from run_generation import diagnose

ORDER = ["legacy", "splitter_fix", "header_fix", "both_fixes"]


def loop_outcome(row: dict, variant: str) -> str:
    if row["outcome"] == "no_evidence_refusal":
        return row["outcome"]
    atts = [a for a in row["attempts"] if "raw" in a]
    if not atts:
        return row["outcome"]
    for i, a in enumerate(atts):
        if a["kind"] in ("refuse_token", "empty"):
            return a["kind"]
        if a[f"ok_{variant}"]:
            return "answered_first_try" if i == 0 else "answered_after_retry"
        if i == 0 and len(atts) == 1:
            return "undetermined"  # production loop stopped after a pass this variant rejects
    return "validator_refusal"


def main(fname: str, used: str) -> None:
    path = RESULTS / fname
    gen = json.loads(path.read_text(encoding="utf-8"))
    for row in gen["rows"]:
        allowed = {c["id"] for c in row["citations"]}
        for a in row["attempts"]:
            if "raw" in a:
                a.update(diagnose(a["raw"], allowed))
    gen["validator_used_in_loop"] = used
    gold = [r for r in gen["rows"] if r["category"] != "negative"]
    variants = {}
    for v in ORDER:
        outs = Counter(loop_outcome(r, v) for r in gold)
        answered = outs["answered_first_try"] + outs["answered_after_retry"]
        variants[v] = {
            "outcomes": dict(outs),
            "answer_rate": answered / len(gold),
            "refusal_rate": 1 - answered / len(gold) if outs["undetermined"] == 0 else None,
            "first_attempt_pass_rate": sum(1 for r in gold for a in r["attempts"][:1] if a.get(f"ok_{v}")) / len(gold),
        }
    gen["validator_variants_gold_questions"] = variants
    dump_json(gen, path)
    print(json.dumps(variants, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
