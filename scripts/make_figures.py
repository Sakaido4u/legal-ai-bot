#!/usr/bin/env python3
"""
Publication-style figures from scripts/batch_query.py outputs.

Reads outputs/results.csv (hits above the threshold). If present, also uses
  outputs/query_summary.csv  so queries with zero hits still appear on charts
  outputs/results_all.csv    so the score histogram shows chunks below the threshold
  outputs/results.json       for the threshold used in the run

Writes 300-dpi PNGs to outputs/figures/:
  score_distribution.png, hits_per_query.png, avg_score_per_query.png,
  risk_breakdown.png (only when risk levels exist), summary_table.png

Usage (PowerShell, from the repo root):
  python scripts/make_figures.py
  python scripts/make_figures.py --in-dir outputs --threshold 0.6
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only; no window needed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DPI = 300

# Palette: one series hue, a neutral for "below threshold", status colors for risk.
SERIES = "#2a78d6"
NEUTRAL = "#b5b4ad"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
RISK_COLORS = {"low": "#0ca30c", "medium": "#fab219", "high": "#d03b3b"}
RISK_ORDER = ["low", "medium", "high"]

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "axes.edgecolor": INK_SECONDARY,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
    }
)


def read_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path, encoding="utf-8-sig") if path.is_file() else None


def load_threshold(in_dir: Path, override: float | None) -> float:
    if override is not None:
        return override
    report = in_dir / "results.json"
    if report.is_file():
        return float(json.loads(report.read_text(encoding="utf-8")).get("threshold", 0.5))
    return 0.5


def build_query_table(hits: pd.DataFrame, summary: pd.DataFrame | None) -> pd.DataFrame:
    """One row per query with an ID (Q1, Q2, ...) in the order they were run."""
    if summary is not None and not summary.empty:
        table = summary[["query", "retrieved_count", "hit_count", "top_score", "avg_score"]].copy()
    else:
        grouped = hits.groupby("query", sort=False)["score"]
        table = pd.DataFrame(
            {
                "query": grouped.size().index,
                "retrieved_count": np.nan,
                "hit_count": grouped.size().values,
                "top_score": grouped.max().values,
                "avg_score": grouped.mean().values,
            }
        )
    table.insert(0, "id", [f"Q{i}" for i in range(1, len(table) + 1)])
    return table.reset_index(drop=True)


def save(fig, out_dir: Path, name: str) -> None:
    path = out_dir / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path}")


def score_distribution(scores_all: pd.DataFrame, threshold: float, out_dir: Path, has_all: bool) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    bins = np.linspace(0, 1, 21)
    below = scores_all.loc[scores_all["score"] <= threshold, "score"]
    above = scores_all.loc[scores_all["score"] > threshold, "score"]
    ax.hist(
        [below, above],
        bins=bins,
        stacked=True,
        color=[NEUTRAL, SERIES],
        edgecolor="white",
        linewidth=1.0,
        label=[f"At or below threshold (n={len(below)})", f"Above threshold (n={len(above)})"],
    )
    ax.axvline(threshold, color=INK, linestyle="--", linewidth=1.2)
    ax.annotate(
        f"threshold = {threshold:.2f}",
        xy=(threshold, 1),
        xycoords=("data", "axes fraction"),
        xytext=(4, -2),
        textcoords="offset points",
        va="top",
        fontsize=8,
        color=INK,
    )
    ax.set_xlim(0, 1)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Relevance score (cosine similarity, 0–1)")
    ax.set_ylabel("Number of retrieved chunks")
    ax.set_title("Distribution of retrieval scores" + ("" if has_all else " (hits only)"))
    ax.legend(loc="upper left", fontsize=8)
    save(fig, out_dir, "score_distribution.png")


def _query_bars(ax, table: pd.DataFrame, values: pd.Series, fmt: str) -> None:
    x = np.arange(len(table))
    ax.bar(x, values.fillna(0), width=0.6, color=SERIES)
    for xi, v in zip(x, values):
        label = "no hits" if pd.isna(v) else fmt.format(v)
        y = 0 if pd.isna(v) else v
        ax.annotate(label, (xi, y), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, table["id"])
    ax.set_xlabel("Query (see summary table for full text)")


def hits_per_query(table: pd.DataFrame, threshold: float, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    _query_bars(ax, table, table["hit_count"].astype(float), "{:.0f}")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, max(1, table["hit_count"].max()) * 1.15)
    ax.set_ylabel(f"Chunks with score > {threshold:.2f}")
    ax.set_title("Relevant chunks retrieved per query")
    save(fig, out_dir, "hits_per_query.png")


def avg_score_per_query(table: pd.DataFrame, threshold: float, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    _query_bars(ax, table, table["avg_score"], "{:.3f}")
    ax.axhline(threshold, color=INK, linestyle="--", linewidth=1.0)
    ax.annotate(f"threshold = {threshold:.2f}", xy=(1, threshold), xycoords=("axes fraction", "data"),
                xytext=(0, 3), textcoords="offset points", ha="right", va="bottom", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean relevance score of hits")
    ax.set_title("Average relevance score per query")
    save(fig, out_dir, "avg_score_per_query.png")


def risk_breakdown(hits: pd.DataFrame, out_dir: Path) -> bool:
    if "risk_level" not in hits.columns:
        return False
    levels = hits["risk_level"].dropna().astype(str).str.lower()
    if levels.empty:
        return False
    order = RISK_ORDER + sorted(set(levels) - set(RISK_ORDER))
    counts = levels.value_counts().reindex(order, fill_value=0)

    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    x = np.arange(len(counts))
    ax.bar(x, counts.values, width=0.6, color=[RISK_COLORS.get(k, NEUTRAL) for k in counts.index])
    for xi, v in zip(x, counts.values):
        ax.annotate(f"{v}", (xi, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, [k.capitalize() for k in counts.index])
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, max(1, counts.max()) * 1.15)
    ax.set_xlabel("Heuristic risk level")
    ax.set_ylabel("Number of relevant chunks")
    ax.set_title("Risk level of relevant chunks")
    save(fig, out_dir, "risk_breakdown.png")
    return True


def summary_table(table: pd.DataFrame, threshold: float, out_dir: Path) -> None:
    def fmt(v, spec):
        return "–" if pd.isna(v) else format(v, spec)

    wrapped = [textwrap.fill(str(q), 50) for q in table["query"]]
    has_retrieved = table["retrieved_count"].notna().any()
    columns = ["ID", "Query"] + (["Retrieved"] if has_retrieved else []) + ["Hits", "Top\nscore", "Avg\nscore"]
    cells = []
    for i, row in table.iterrows():
        cell = [row["id"], wrapped[i]]
        if has_retrieved:
            cell.append(fmt(row["retrieved_count"], ".0f"))
        cell += [fmt(row["hit_count"], ".0f"), fmt(row["top_score"], ".3f"), fmt(row["avg_score"], ".3f")]
        cells.append(cell)

    # Row heights in inches: header has two lines; body rows grow with wrapped text.
    line_counts = [w.count("\n") + 1 for w in wrapped]
    row_heights = [0.4] + [0.17 * n + 0.13 for n in line_counts]
    fig_h = sum(row_heights)
    fig, ax = plt.subplots(figsize=(7.2, fig_h))
    ax.axis("off")
    widths = [0.06, 0.52] + ([0.12] if has_retrieved else []) + [0.08, 0.11, 0.11]
    # bbox fills the axes exactly; cell heights below are scaled to fit it.
    tbl = ax.table(cellText=cells, colLabels=columns, colWidths=widths, bbox=[0, 0, 1, 1], cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.6)
        cell.set_height(row_heights[r])
        if r == 0:
            cell.set_text_props(weight="bold", color=INK)
            cell.set_facecolor("#f0efec")
        if c == 1 and r > 0:
            cell.set_text_props(ha="left")
            cell.PAD = 0.02
    ax.set_title(f"Batch query summary (relevance threshold = {threshold:.2f})", pad=6)
    save(fig, out_dir, "summary_table.png")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Make paper figures from batch query outputs.")
    p.add_argument("--in-dir", type=Path, default=ROOT / "outputs", help="folder with results.csv")
    p.add_argument("--out-dir", type=Path, default=None, help="default: <in-dir>/figures")
    p.add_argument("--threshold", type=float, default=None, help="default: value stored in results.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_dir: Path = args.in_dir
    out_dir: Path = args.out_dir or in_dir / "figures"

    hits = read_csv(in_dir / "results.csv")
    if hits is None:
        raise SystemExit(f"{in_dir / 'results.csv'} not found. Run scripts/batch_query.py first.")
    summary = read_csv(in_dir / "query_summary.csv")
    all_rows = read_csv(in_dir / "results_all.csv")
    threshold = load_threshold(in_dir, args.threshold)
    if args.threshold is not None and all_rows is not None:
        # Re-apply a different threshold to the saved scores.
        hits = all_rows[all_rows["score"] > threshold].copy()
        if summary is not None:
            g = hits.groupby("query")["score"]
            summary = summary.copy()
            summary["hit_count"] = summary["query"].map(g.size()).fillna(0).astype(int)
            summary["top_score"] = summary["query"].map(g.max())
            summary["avg_score"] = summary["query"].map(g.mean())

    table = build_query_table(hits, summary)
    if table.empty:
        raise SystemExit("No queries found in the outputs.")

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Threshold {threshold:.2f} | {len(table)} queries | {len(hits)} hits")
    score_distribution(all_rows if all_rows is not None else hits, threshold, out_dir, all_rows is not None)
    hits_per_query(table, threshold, out_dir)
    avg_score_per_query(table, threshold, out_dir)
    if not risk_breakdown(hits, out_dir):
        print("  skipped risk_breakdown.png (no risk levels in results)")
    summary_table(table, threshold, out_dir)


if __name__ == "__main__":
    main()
