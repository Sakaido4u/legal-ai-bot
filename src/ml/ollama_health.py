from __future__ import annotations

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def ollama_reachable(base_url: str, timeout: float = 3.0) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def ollama_has_model(base_url: str, model: str, timeout: float = 5.0) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = {m.get("name", "").split(":")[0] for m in r.json().get("models", [])}
        base = model.split(":")[0]
        return base in names
    except requests.RequestException:
        return False


def check_ollama_llm(base_url: str, model: str) -> dict:
    ok = ollama_reachable(base_url)
    has_model = ollama_has_model(base_url, model) if ok else False
    return {
        "reachable": ok,
        "model": model,
        "model_available": has_model,
        "status": "ok" if ok and has_model else ("degraded" if ok else "unavailable"),
    }


def resolve_embedding_model_path(model_name: str, repo_root: Path | None = None) -> str:
    """Allow COMPLIANCE_EMBEDDING_MODEL=models/compliance-embeddings local paths."""
    if not model_name.startswith("models/"):
        return model_name
    root = repo_root or Path(__file__).resolve().parents[2]
    local = root / model_name
    if local.is_dir():
        return str(local)
    return model_name
