#!/usr/bin/env python3
"""Fine-tune sentence embeddings on regulatory corpus, then rebuild FAISS index."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ml.embedding_finetune import finetune_embeddings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--base-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument(
        "--output-index",
        type=Path,
        default=ROOT / "vector_store" / "regulatory-finetuned",
    )
    args = parser.parse_args()

    out = finetune_embeddings(base_model=args.base_model, epochs=args.epochs)
    rel_model = out.relative_to(ROOT).as_posix()

    build = [
        sys.executable,
        str(ROOT / "scripts" / "build_corpus_index.py"),
        "--embedding-model",
        str(out),
        "--output",
        str(args.output_index),
    ]
    print(f"Rebuilding index with fine-tuned model at {rel_model} ...")
    subprocess.run(build, check=True, cwd=ROOT)
    print(f"Done. Set COMPLIANCE_EMBEDDING_MODEL={rel_model}")
    print(f"Set COMPLIANCE_INDEX_DIR={args.output_index.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
