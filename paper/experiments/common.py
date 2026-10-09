"""Shared helpers for the paper experiments.

All scripts in this directory are run from the repository root with
``PYTHONPATH=src``.  Results are written to ``paper/experiments/results``.
"""

from __future__ import annotations

import bisect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXP_DIR = Path(__file__).resolve().parent
RESULTS = EXP_DIR / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

INDEX_DIR = ROOT / "vector_store" / "regulatory"
FINETUNED_INDEX_DIR = ROOT / "vector_store" / "regulatory-finetuned"
FINETUNED_MODEL = ROOT / "models" / "compliance-embeddings"
BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

PDFS = {
    "GDPR": ROOT / "documents" / "gdpr" / "gdpr_2016_679.pdf",
    "DPDP": ROOT / "documents" / "dpdp" / "dpdp_act_2023.pdf",
}

_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


class NormalizedDoc:
    """Whitespace-normalized document text with a map back to raw offsets."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        out: list[str] = []
        offsets: list[int] = []
        prev_space = True
        for i, ch in enumerate(raw):
            if ch.isspace():
                if prev_space:
                    continue
                out.append(" ")
                offsets.append(i)
                prev_space = True
            else:
                out.append(ch)
                offsets.append(i)
                prev_space = False
        self.text = "".join(out).rstrip()
        self.offsets = offsets[: len(self.text)]

    def raw_to_norm(self, raw_pos: int) -> int:
        return bisect.bisect_left(self.offsets, raw_pos)


def load_pdf_text(path: Path) -> str:
    import fitz

    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def gdpr_article_boundaries(raw: str) -> list[tuple[int, str]]:
    """Sequential 'Article N' heading lines in the operative part (after CHAPTER I)."""
    start = raw.find("CHAPTER I")
    bounds: list[tuple[int, str]] = [(0, "Recital")]
    expected = 1
    for m in re.finditer(r"^[ \t]*Article[ \t]+(\d+)[ \t]*$", raw, re.M):
        if m.start() < start:
            continue
        n = int(m.group(1))
        if n == expected:
            bounds.append((m.start(), f"Article {n}"))
            expected += 1
    return bounds


def dpdp_section_boundaries(raw: str) -> list[tuple[int, str]]:
    """Sequential 'N. ' section starts for the DPDP Act, 2023 (sections 1-44 + Schedule)."""
    bounds: list[tuple[int, str]] = [(0, "Preamble")]
    expected = 1
    for m in re.finditer(r"^[ \t]*(\d{1,2})\.[ \t]+(?=\(1\)|[A-Z])", raw, re.M):
        n = int(m.group(1))
        if n == expected:
            bounds.append((m.start(), f"Section {n}"))
            expected += 1
            if expected > 44:
                break
    sched = raw.rfind("THE SCHEDULE")
    if sched > 0 and bounds and sched > bounds[-1][0]:
        bounds.append((sched, "Schedule"))
    return bounds


def label_at(bounds_norm: list[tuple[int, str]], pos: int) -> str:
    keys = [b[0] for b in bounds_norm]
    i = bisect.bisect_right(keys, pos) - 1
    return bounds_norm[max(0, i)][1]


def labels_spanning(bounds_norm: list[tuple[int, str]], start: int, end: int) -> list[str]:
    """All statutory units overlapped by the span [start, end)."""
    keys = [b[0] for b in bounds_norm]
    i = max(0, bisect.bisect_right(keys, start) - 1)
    j = max(0, bisect.bisect_right(keys, max(start, end - 1)) - 1)
    return [bounds_norm[k][1] for k in range(i, j + 1)]


def locate(doc: NormalizedDoc, chunk_text: str) -> int | None:
    """Find a chunk inside the normalized document using several probes."""
    t = norm(chunk_text)
    # Strip a leading synthetic heading ("Article 17 Right to erasure ...") if present
    probes = []
    for start in (0, 40, len(t) // 2, max(0, len(t) - 120)):
        if start < len(t):
            probes.append(t[start : start + 60])
    for p in probes:
        if len(p) < 20:
            continue
        i = doc.text.find(p)
        if i >= 0:
            return i
    return None


def load_meta(index_dir: Path, jurisdiction: str) -> list[dict]:
    path = index_dir / f"meta_{jurisdiction}.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def dump_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def bootstrap_ci(values: list[float], n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean and 95% percentile bootstrap CI over per-question values."""
    import numpy as np

    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    means = arr[idx].mean(axis=1)
    return float(arr.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
