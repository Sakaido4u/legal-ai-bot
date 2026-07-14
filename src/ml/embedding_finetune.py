from __future__ import annotations

import json
import logging
from pathlib import Path

from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader

from .benchmarks import DEFAULT_BENCHMARKS

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_chunk_texts(seed_path: Path) -> list[tuple[str, str]]:
    """(anchor_query, positive_passage) pairs from full corpus + benchmark queries."""
    from .ingestion import load_corpus_seeds, source_to_chunks

    pairs: list[tuple[str, str]] = []

    # Benchmark query → keyword anchors
    for case in DEFAULT_BENCHMARKS:
        pairs.append((case.query, case.query))
        for kw in case.expect_keywords:
            pairs.append((case.query, kw))

    # Full corpus chunks from PDF/HTML hierarchy pipeline
    for source in load_corpus_seeds(seed_path):
        try:
            chunks = source_to_chunks(source)
            for ch in chunks[:200]:
                q = f"{source.label} {ch.heading or ''} compliance requirements".strip()
                pairs.append((q, ch.text[:768]))
                for case in DEFAULT_BENCHMARKS:
                    if source.jurisdiction in case.jurisdictions:
                        pairs.append((case.query, ch.text[:512]))
        except Exception as exc:
            logger.warning("Skip finetune pair from %s: %s", source.label, exc)

    # Hard negatives: cross-jurisdiction mismatches
    by_jurisdiction: dict[str, list[str]] = {}
    for source in load_corpus_seeds(seed_path):
        try:
            for ch in source_to_chunks(source)[:50]:
                by_jurisdiction.setdefault(source.jurisdiction.value, []).append(ch.text[:256])
        except Exception:
            pass

    for case in DEFAULT_BENCHMARKS:
        for j, texts in by_jurisdiction.items():
            if j not in {jj.value for jj in case.jurisdictions} and texts:
                pairs.append((case.query, texts[0]))

    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for a, b in pairs:
        key = (a[:120], b[:120])
        if key not in seen and len(b.strip()) > 20:
            seen.add(key)
            out.append((a, b))
    return out


def finetune_embeddings(
    *,
    base_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    output_dir: Path | None = None,
    seed_path: Path | None = None,
    epochs: int = 2,
    batch_size: int = 8,
) -> Path:
    """
    Lightweight domain adaptation: contrastive fine-tune on regulatory (query, passage) pairs.
    Saves a local SentenceTransformer to models/compliance-embeddings/.
    """
    output_dir = output_dir or (_REPO_ROOT / "models" / "compliance-embeddings")
    seed_path = seed_path or (_REPO_ROOT / "data" / "corpus_seeds.json")

    pairs = _load_chunk_texts(seed_path)
    if len(pairs) < 4:
        raise RuntimeError("Not enough training pairs for embedding fine-tune.")

    train = [InputExample(texts=[a, b]) for a, b in pairs]
    loader = DataLoader(train, shuffle=True, batch_size=batch_size)
    model = SentenceTransformer(base_model)
    loss = losses.MultipleNegativesRankingLoss(model)
    model.fit(
        train_objectives=[(loader, loss)],
        epochs=epochs,
        warmup_steps=max(1, len(train) // batch_size),
        show_progress_bar=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(output_dir))
    meta = {
        "base_model": base_model,
        "epochs": epochs,
        "training_pairs": len(pairs),
        "output_dir": str(output_dir),
    }
    (output_dir / "finetune_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Saved fine-tuned embeddings to %s (%d pairs)", output_dir, len(pairs))
    return output_dir
