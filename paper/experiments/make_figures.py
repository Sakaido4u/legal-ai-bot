"""Build the paper's figures (PDF) and LaTeX table fragments from results/*.json."""

from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import RESULTS

FIG = RESULTS.parents[1] / "figures"
TAB = RESULTS.parents[1] / "tables"
FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})

CONFIG_LABELS = {
    "system": "Full system (dense, part., MMR)",
    "no_mmr": "w/o MMR",
    "no_dedupe": "w/o article dedupe",
    "no_expansion": "w/o query expansion",
    "no_floor": "w/o similarity floor",
    "global_index": "Global index (no partition)",
    "fixed_chunks": "Fixed 900/120 chunks",
    "finetuned": "Fine-tuned encoder",
    "bm25": "BM25 (lexical)",
    "hybrid_rrf": "Hybrid RRF (dense+BM25)",
    "no_recitals": "Operative-only index",
    "no_recitals_no_mmr": "Operative-only, w/o MMR",
    "no_recitals_hybrid": "Operative-only, hybrid RRF",
}


def fmt_ci(d: dict, pct: bool = False) -> str:
    m, (lo, hi) = d["mean"], d["ci95"]
    if pct:
        return f"{100*m:.1f} [{100*lo:.1f}, {100*hi:.1f}]"
    return f"{m:.3f} [{lo:.3f}, {hi:.3f}]"


def retrieval_outputs() -> None:
    r = json.loads((RESULTS / "retrieval_results.json").read_text(encoding="utf-8"))
    s = r["summary"]
    order = [k for k in CONFIG_LABELS if k in s]

    # Figure: hit@8 and MRR with CIs
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    for ax, metric, title in zip(axes, ("hit@8", "mrr@8"), ("Unit-level Hit@8", "MRR@8")):
        means = [s[k][metric]["mean"] for k in order]
        lo = [s[k][metric]["mean"] - s[k][metric]["ci95"][0] for k in order]
        hi = [s[k][metric]["ci95"][1] - s[k][metric]["mean"] for k in order]
        y = np.arange(len(order))[::-1]
        colors = ["#2b6cb0" if k == "system" else ("#718096" if not k.startswith("no_recitals") and k not in ("bm25", "hybrid_rrf") else "#2f855a") for k in order]
        ax.barh(y, means, xerr=[lo, hi], color=colors, capsize=2, height=0.65)
        ax.set_yticks(y)
        ax.set_yticklabels([CONFIG_LABELS[k] for k in order])
        ax.set_xlim(0, 1)
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        for yi, m in zip(y, means):
            ax.text(min(m + 0.02, 0.98), yi, f"{m:.2f}", va="center", fontsize=7)
    axes[0].set_xlabel("Hit@8 (72 labelled questions, 95% bootstrap CI)")
    axes[1].set_xlabel("MRR@8")
    fig.tight_layout()
    fig.savefig(FIG / "retrieval_ablation.pdf")
    plt.close(fig)

    # Figure: per-category hit@8 for selected configs
    cats = ["gdpr", "dpdp", "ccpa", "cross", "ambiguous"]
    sel = ["system", "no_mmr", "bm25", "hybrid_rrf", "no_recitals_hybrid"]
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    w = 0.16
    x = np.arange(len(cats))
    for i, k in enumerate(sel):
        vals = [s[k]["by_category_hit@8"].get(c, {}).get("mean", 0) for c in cats]
        ax.bar(x + (i - 2) * w, vals, w, label=CONFIG_LABELS[k])
    ns = [s["system"]["by_category_hit@8"][c]["n"] for c in cats]
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c.upper() if c != 'ambiguous' else 'Ambig.'}\n(n={n})" for c, n in zip(cats, ns)])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Hit@8")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=7, ncol=2, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "retrieval_by_category.pdf")
    plt.close(fig)

    # Table: main retrieval results
    lines = [
        r"\begin{tabular}{@{}lccccr@{}}",
        r"\toprule",
        r"Configuration & Hit@4 & Hit@8 & MRR@8 & $\Delta$Hit@8 vs.\ full & ms \\",
        r"\midrule",
    ]
    for k in order:
        d = s[k]
        delta = "--" if k == "system" else _delta(r["paired_diff_vs_system"][k]["hit@8"])
        lines.append(
            f"{CONFIG_LABELS[k]} & {d['hit@4']['mean']:.3f} & {fmt_ci(d['hit@8'])} & {d['mrr@8']['mean']:.3f} & {delta} & {d['latency_ms_mean']:.1f} \\\\"
        )
        if k in ("no_floor", "finetuned", "hybrid_rrf"):
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "retrieval_main.tex").write_text("\n".join(lines), encoding="utf-8")

    # Table: jurisdiction precision / negatives
    lines = [
        r"\begin{tabular}{@{}lcccc@{}}",
        r"\toprule",
        r"Configuration & Juris.\ precision & Cross-juris.\ coverage & Neg.: any passage & Neg.: flagged $<0.50$ \\",
        r"\midrule",
    ]
    for k in ("system", "global_index", "bm25", "hybrid_rrf"):
        d = s[k]
        cov = d.get("cross_jurisdiction_coverage", {}).get("mean", float("nan"))
        neg = d["negative"]
        flagged = neg["flagged_low_confidence(<0.50)"]
        flagged_s = f"{flagged:.2f}" if k not in ("bm25", "hybrid_rrf") else "n/a"
        lines.append(f"{CONFIG_LABELS[k]} & {d['jurisdiction_precision']['mean']:.3f} & {cov:.2f} & {neg['returned_any_passage']:.2f} & {flagged_s} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "retrieval_jurisdiction.tex").write_text("\n".join(lines), encoding="utf-8")

    # Table: legacy six-case benchmark keyword vs unit-level
    leg = r["legacy_six_case_benchmark"]
    lines = [r"\begin{tabular}{@{}lccl@{}}", r"\toprule", r"Case & Keyword check & Unit-level Hit@4 & Top-4 units retrieved \\", r"\midrule"]
    for c in leg["mmr_on"]["cases"]:
        u = leg["unit_level"][c["name"]]
        lines.append(
            f"\\texttt{{{c['name'].replace('_', '\\_')}}} & {'pass' if c['passed'] else 'fail'} & {'1' if u['hit@4'] else '0'} & {', '.join(x.replace('_', '\\_') for x in u['top_units'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "legacy_six.tex").write_text("\n".join(lines), encoding="utf-8")


def _delta(d: dict) -> str:
    m, (lo, hi) = d["mean_diff"], d["ci95"]
    sig = "*" if (lo > 0 or hi < 0) else ""
    return f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]{sig}"


def mmr_outputs() -> None:
    before = json.loads((RESULTS / "mmr_profile_before.json").read_text(encoding="utf-8"))
    after = json.loads((RESULTS / "mmr_profile_after.json").read_text(encoding="utf-8"))
    st = before["stage_summary_ms"]
    stages = [
        ("Sub-query encoding", st["encode_queries_ms"]["mean"]),
        ("FAISS search", st["faiss_search_ms"]["mean"]),
        ("Article dedupe", st["dedupe_ms"]["mean"]),
        ("MMR: re-encode query", st["mmr_reencode_query_ms"]["mean"]),
        ("MMR: re-encode candidates", st["mmr_reencode_candidates_ms"]["mean"]),
        ("MMR: selection loop", st["mmr_select_loop_ms"]["mean"]),
    ]
    fig, ax = plt.subplots(figsize=(5.0, 2.6))
    y = np.arange(len(stages))[::-1]
    vals = [v for _, v in stages]
    ax.barh(y, vals, color=["#718096"] * 3 + ["#c53030"] * 2 + ["#718096"])
    ax.set_yticks(y)
    ax.set_yticklabels([n for n, _ in stages])
    ax.set_xlabel("Mean time per query (ms, CPU)")
    for yi, v in zip(y, vals):
        ax.text(v + 1, yi, f"{v:.1f}", va="center", fontsize=7)
    ax.set_xlim(0, max(vals) * 1.2)
    fig.tight_layout()
    fig.savefig(FIG / "mmr_profile.pdf")
    plt.close(fig)

    e_b, e_a = before["end_to_end"], after["end_to_end"]
    lines = [
        r"\begin{tabular}{@{}lcc@{}}",
        r"\toprule",
        r"Retriever & MMR on (ms) & MMR off (ms) \\",
        r"\midrule",
        f"Original (re-embeds candidates) & {e_b['mmr_on']['mean_ms']:.1f} $\\pm$ {e_b['mmr_on']['sd_ms']:.1f} & {e_b['mmr_off']['mean_ms']:.1f} $\\pm$ {e_b['mmr_off']['sd_ms']:.1f} \\\\",
        f"Fixed (reads vectors from index) & {e_a['mmr_on']['mean_ms']:.1f} $\\pm$ {e_a['mmr_on']['sd_ms']:.1f} & {e_a['mmr_off']['mean_ms']:.1f} $\\pm$ {e_a['mmr_off']['sd_ms']:.1f} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
    ]
    (TAB / "mmr_latency.tex").write_text("\n".join(lines), encoding="utf-8")


def generation_outputs() -> None:
    files = sorted(glob.glob(str(RESULTS / "generation_*.json")))
    if not files:
        return
    runs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in files]
    MODEL_LABEL = {"compliance-llm": "Llama 3.2 3B (Q4)", "llama3.1:8b": "Llama 3.1 8B (Q4)"}
    fixed = [g for g in runs if g.get("validator_used_in_loop") == "both_fixes"]
    legacy_run = next((g for g in runs if g.get("validator_used_in_loop") == "splitter_fix"), None)
    by_model: dict[str, list[dict]] = {}
    for g in sorted(fixed, key=lambda g: (g["model"] != "compliance-llm", g["tag"])):
        by_model.setdefault(g["model"], []).append(g)

    def kinds_share(gs: list[dict], key: str = "kind") -> dict:
        """Share of first-attempt outcome kinds over labelled questions (mean over runs)."""
        agg = {name: [] for name in ("valid", "refuse_token", "invalid_citation_id", "uncited_sentence", "header_line", "malformed_tag")}
        for g in gs:
            firsts = [r["attempts"][0] for r in g["rows"] if r["category"] != "negative" and r["attempts"] and "raw" in r["attempts"][0]]
            c = Counter(a.get(key, a["kind"]) for a in firsts)
            for name in agg:
                agg[name].append(c.get(name, 0) / max(1, len(firsts)))
        return {k: float(np.mean(v)) for k, v in agg.items()}

    # ---- Main table: answer / refusal rates --------------------------------------------------
    lines = [
        r"\begin{tabular}{@{}llcccc@{}}",
        r"\toprule",
        r"Model & Validator & Runs & Answer rate (\%) & Refusal (\%) & s/question \\",
        r"\midrule",
    ]
    if legacy_run is not None:
        v = legacy_run["validator_variants_gold_questions"]["legacy"]
        lat = legacy_run["summary_gold_questions"]["mean_total_latency_ms"] / 1000
        lines.append(f"{MODEL_LABEL.get(legacy_run['model'], legacy_run['model'])} & original (re-scored) & 1 & {100*v['answer_rate']:.1f} & {100*v['refusal_rate']:.1f} & {lat:.1f} \\\\")
    for model, gs in by_model.items():
        ar = np.array([g["summary_gold_questions"]["answer_rate"] for g in gs])
        lat = np.mean([g["summary_gold_questions"]["mean_total_latency_ms"] for g in gs]) / 1000
        sd = f" $\\pm$ {100*ar.std(ddof=1):.1f}" if len(gs) > 1 else ""
        lines.append(f"{MODEL_LABEL.get(model, model)} & fixed & {len(gs)} & {100*ar.mean():.1f}{sd} & {100*(1-ar.mean()):.1f} & {lat:.1f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "generation_main.tex").write_text("\n".join(lines), encoding="utf-8")

    # ---- Validator ablation (post hoc on logged 3B outputs) ----------------------------------
    if legacy_run is not None:
        vv = legacy_run["validator_variants_gold_questions"]
        idonly = legacy_run["summary_gold_questions"]["first_attempt_pass_rate_id_only"]
        lines = [
            r"\begin{tabular}{@{}lcc@{}}",
            r"\toprule",
            r"Validator variant & First-attempt pass (\%) & Loop refusal (\%) \\",
            r"\midrule",
            f"Valid citation ids only (no per-sentence rule) & {100*idonly:.1f} & -- \\\\",
            f"Per-sentence, original & {100*vv['legacy']['first_attempt_pass_rate']:.1f} & {100*vv['legacy']['refusal_rate']:.1f} \\\\",
            f"\\quad + abbreviation-aware sentence splitter & {100*vv['splitter_fix']['first_attempt_pass_rate']:.1f} & {100*vv['splitter_fix']['refusal_rate']:.1f} \\\\",
            f"\\quad + ignore list-introducer lines & {100*vv['header_fix']['first_attempt_pass_rate']:.1f} & {100*vv['header_fix']['refusal_rate']:.1f} \\\\",
            f"\\quad + both (deployed) & {100*vv['both_fixes']['first_attempt_pass_rate']:.1f} & {100*vv['both_fixes']['refusal_rate']:.1f} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
        ]
        (TAB / "validator_ablation.tex").write_text("\n".join(lines), encoding="utf-8")

    # ---- Refusal by category (fixed validator) -----------------------------------------------
    cats = ["gdpr", "dpdp", "ccpa", "cross", "ambiguous", "negative"]
    lines = [r"\begin{tabular}{@{}l" + "c" * len(cats) + "@{}}", r"\toprule", "Model & " + " & ".join(c.upper() if c not in ("ambiguous", "negative") else c.capitalize() for c in cats) + r" \\", r"\midrule"]
    for model, gs in by_model.items():
        vals = []
        for c in cats:
            if c == "negative":
                v = np.mean([g["summary_negative_questions"]["refusal_rate"] for g in gs])
            else:
                v = np.mean([g["summary_gold_questions"]["by_category_refusal"].get(c, float("nan")) for g in gs])
            vals.append(f"{100*v:.0f}")
        lines.append(f"{MODEL_LABEL.get(model, model)} & " + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "refusal_by_category.tex").write_text("\n".join(lines), encoding="utf-8")

    # ---- Figure: first-attempt outcome under original vs fixed validator ---------------------
    rows_fig = []
    if legacy_run is not None:
        rows_fig.append(("3B, original validator", kinds_share([legacy_run], "legacy_kind")))
    for model, gs in by_model.items():
        rows_fig.append((MODEL_LABEL.get(model, model).replace("Llama ", "") + ", fixed validator", kinds_share(gs)))
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    y = np.arange(len(rows_fig))[::-1]
    left = np.zeros(len(rows_fig))
    for key, lab, col in (
        ("valid", "Passes validator", "#2f855a"),
        ("header_line", "Only an uncited list-introducer line", "#ecc94b"),
        ("uncited_sentence", "Uncited factual sentence", "#dd6b20"),
        ("malformed_tag", "Malformed tag, e.g. (C0)", "#b7791f"),
        ("invalid_citation_id", "Hallucinated citation id", "#c53030"),
        ("refuse_token", "Model emitted REFUSE", "#4a5568"),
    ):
        vals = np.array([r[1][key] for r in rows_fig])
        ax.barh(y, vals, left=left, label=lab, color=col, height=0.55)
        for yi, l, v in zip(y, left, vals):
            if v > 0.07:
                ax.text(l + v / 2, yi, f"{100*v:.0f}%", ha="center", va="center", color="white", fontsize=7)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows_fig])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of first-attempt generations (72 labelled questions)")
    ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "refusal_diagnosis.pdf", bbox_inches="tight")
    plt.close(fig)


def faithfulness_outputs() -> None:
    p = RESULTS / "faithfulness.json"
    if not p.is_file():
        return
    f = json.loads(p.read_text(encoding="utf-8"))
    lines = [
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"Model & Answers & Claims & Entailed (cited) & Neutral & Contradicted & Supported, mis-cited \\",
        r"\midrule",
    ]
    fig, ax = plt.subplots(figsize=(4.8, 2.6))
    for i, (fname, d) in enumerate(f.items()):
        if "summary" not in d:
            continue
        s = d["summary"]
        label = {"compliance-llm": "Llama 3.2 3B", "llama3.1:8b": "Llama 3.1 8B"}.get(s["model"], s["model"])
        lines.append(
            f"{label} & {s['n_answers']} & {s['n_claims']} & {100*s['entailed_by_cited_excerpt']:.1f}\\% & {100*s['neutral_wrt_cited_excerpt']:.1f}\\% & {100*s['contradicted_by_cited_excerpt']:.1f}\\% & {100*s['supported_but_miscited']:.1f}\\% \\\\"
        )
        pe = [c["p_entail_cited"] for c in d["claims"]]
        ax.hist(pe, bins=20, range=(0, 1), alpha=0.6, label=label)
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "faithfulness.tex").write_text("\n".join(lines), encoding="utf-8")
    ax.set_xlabel("P(entailment) of claim given its cited excerpt")
    ax.set_ylabel("Claims")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "faithfulness_hist.pdf")
    plt.close(fig)


def per_question_table() -> None:
    """Appendix: per-question retrieval and generation outcomes (two half tables)."""
    questions = json.loads((RESULTS.parent / "questions.json").read_text(encoding="utf-8"))["questions"]
    r = json.loads((RESULTS / "retrieval_results.json").read_text(encoding="utf-8"))["per_question"]
    sysr = {x["id"]: x for x in r["system"]}
    bm = {x["id"]: x for x in r["bm25"]}
    oh = {x["id"]: x for x in r["no_recitals_hybrid"]}
    gens = {}
    for tag, key in (("generation_llama3.2-3b_fixed_run1.json", "3B"), ("generation_llama3.1-8b_fixed_run1.json", "8B")):
        p = RESULTS / tag
        if p.is_file():
            gens[key] = {x["id"]: x["outcome"] for x in json.loads(p.read_text(encoding="utf-8"))["rows"]}
    abbrev = lambda o: {"answered_first_try": "A1", "answered_after_retry": "A2", "refuse_token": "R", "no_evidence_refusal": "N", "empty": "E", "error": "Err"}.get(o.split(":")[0], "V")

    def esc(s: str) -> str:
        return s.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%").replace("'", "'")

    def gold_str(q):
        if not q["gold"]:
            return "--"
        parts = []
        for j, us in q["gold"].items():
            parts.append(", ".join(u.replace("Article ", "Art.\\,").replace("Section ", "S.\\,").replace("_", r"\_") for u in us) + (f" ({j})" if len(q["gold"]) > 1 else ""))
        return "; ".join(parts)

    def rows_for(qs):
        out = []
        for q in qs:
            qid = q["id"]
            hit = lambda d: ("--" if q["category"] == "negative" else ("1" if d[qid]["hit@8"] else "0"))
            txt = q["query"]
            if len(txt) > 78:
                txt = txt[:75].rstrip() + "..."
            g3 = abbrev(gens["3B"][qid]) if "3B" in gens else "--"
            g8 = abbrev(gens["8B"][qid]) if "8B" in gens else "--"
            out.append(f"{qid} & {esc(txt)} & {gold_str(q)} & {hit(sysr)} & {hit(bm)} & {hit(oh)} & {g3} & {g8} \\\\")
        return out

    header = [
        r"\begin{tabular}{@{}llp{3.1cm}cccc c@{}}",
        r"\toprule",
        r"ID & Question & Gold unit(s) & Sys & BM25 & Op-hyb & 3B & 8B \\",
        r"\midrule",
    ]
    half = (len(questions) + 1) // 2
    for i, chunk in enumerate((questions[:half], questions[half:])):
        lines = header + rows_for(chunk) + [r"\bottomrule", r"\end{tabular}"]
        (TAB / f"per_question_{i+1}.tex").write_text("\n".join(lines), encoding="utf-8")


def risk_outputs() -> None:
    r = json.loads((RESULTS / "risk_analysis.json").read_text(encoding="utf-8"))
    lv = r["level_distribution"]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6))
    ax = axes[0]
    names = ["low", "medium", "high"]
    ax.bar(names, [lv[n]["count"] for n in names], color=["#2f855a", "#d69e2e", "#c53030"])
    for i, n in enumerate(names):
        ax.text(i, lv[n]["count"] + 8, f"{lv[n]['count']} ({100*lv[n]['share']:.0f}%)", ha="center", fontsize=7)
    ax.set_ylabel("Indexed chunks (n=712)")
    ax.set_title("Heuristic risk level over the whole index", fontsize=8, fontweight="bold")
    ax = axes[1]
    fr = r["factor_fire_rate"]
    keys = [("obligation", "Obligation (`shall')"), ("prohibit", "Prohibition"), ("penalty", "Penalty"), ("sensitive", "Sensitive data")]
    ax.barh([k[1] for k in keys][::-1], [fr[k[0]] for k in keys][::-1], color="#2b6cb0")
    ax.set_xlabel("Share of chunks where the lexicon factor fires")
    ax.set_xlim(0, 0.5)
    fig.tight_layout()
    fig.savefig(FIG / "risk_distribution.pdf")
    plt.close(fig)


def corpus_table() -> None:
    m = json.loads((RESULTS / "chunk_unit_map.json").read_text(encoding="utf-8"))["stats"]
    lines = [
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Jurisdiction & Source & Chunks & Heading field wrong & Units covered \\",
        r"\midrule",
        f"GDPR & Regulation (EU) 2016/679 (OJ PDF, 88 pp.) & 600 & {m['heading_field_disagrees_with_position']['GDPR']['count']} ({100*m['heading_field_disagrees_with_position']['GDPR']['rate']:.0f}\\%) & {m['operative_units_covered']['GDPR']}/99 articles \\\\",
        f"DPDP & Digital Personal Data Protection Act, 2023 (PDF, 21 pp.) & 105 & {m['heading_field_disagrees_with_position']['DPDP']['count']} ({100*m['heading_field_disagrees_with_position']['DPDP']['rate']:.0f}\\%) & {m['operative_units_covered']['DPDP']}/44 sections \\\\",
        r"CCPA & California OAG CCPA overview (HTML snapshot) & 7 & -- & 7 topic-tagged chunks \\",
        r"\midrule",
        f"\\multicolumn{{5}}{{@{{}}l}}{{Of the 600 GDPR chunks, {m['recital_chunks_gdpr']} ({100*m['recital_chunks_gdpr']/600:.0f}\\%) are recital text; 292 are operative articles.}} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
    ]
    (TAB / "corpus.tex").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    corpus_table()
    retrieval_outputs()
    mmr_outputs()
    risk_outputs()
    generation_outputs()
    faithfulness_outputs()
    per_question_table()
    print("figures ->", FIG)
    print("tables  ->", TAB)
