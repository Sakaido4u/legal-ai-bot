#!/usr/bin/env python3
"""Pull base Ollama model and create compliance-llm custom model."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = Path(__file__).resolve().parents[1]  # placeholder


def main() -> None:
    import os

    ollama = os.environ.get("OLLAMA_EXE") or str(
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    )
    if not Path(ollama).is_file():
        ollama = "ollama"

    modelfile = ROOT / "ollama" / "Modelfile"
    print("Pulling llama3.2 (first run downloads ~2GB)...")
    subprocess.run([ollama, "pull", "llama3.2"], check=True)
    print("Creating compliance-llm from Modelfile...")
    subprocess.run([ollama, "create", "compliance-llm", "-f", str(modelfile)], check=True)
    print("Done. compliance-llm is ready.")


if __name__ == "__main__":
    main()
