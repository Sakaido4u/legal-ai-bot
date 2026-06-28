from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class DocumentVersion:
    """
    Minimal version-tracking metadata for legal sources.

    - sha256 lets you detect silent upstream edits.
    - effective_date/amendment_date can be populated from known release notes.
    - supersedes/superseded_by supports chaining versions over time.
    """

    doc_id: str
    jurisdiction: str
    title: str
    source_url: str
    local_path: str
    downloaded_at: str
    sha256: str
    effective_date: str | None = None
    amendment_date: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"documents": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _upsert_document(manifest: dict[str, Any], record: DocumentVersion) -> None:
    docs: list[dict[str, Any]] = list(manifest.get("documents", []))
    idx = next((i for i, d in enumerate(docs) if d.get("doc_id") == record.doc_id), None)
    payload = {
        "doc_id": record.doc_id,
        "jurisdiction": record.jurisdiction,
        "title": record.title,
        "source_url": record.source_url,
        "local_path": record.local_path,
        "downloaded_at": record.downloaded_at,
        "sha256": record.sha256,
        "effective_date": record.effective_date,
        "amendment_date": record.amendment_date,
        "supersedes": record.supersedes,
        "superseded_by": record.superseded_by,
    }
    if idx is None:
        docs.append(payload)
    else:
        docs[idx] = payload
    manifest["documents"] = docs


def download_document(
    *,
    doc_id: str,
    jurisdiction: str,
    title: str,
    source_url: str,
    target_dir: Path,
    filename: str,
    manifest_path: Path,
    effective_date: str | None = None,
    amendment_date: str | None = None,
    supersedes: str | None = None,
    superseded_by: str | None = None,
    timeout_s: int = 30,
    min_bytes: int = 1,
) -> DocumentVersion:
    """
    Download a document into target_dir/filename and upsert a record in manifest.json.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / filename

    resp = requests.get(source_url, timeout=timeout_s, headers={"User-Agent": "legal-ai-bot/0.1"})
    resp.raise_for_status()
    content = resp.content
    if len(content) < int(min_bytes):
        raise RuntimeError(f"Downloaded content too small ({len(content)} bytes) from {source_url}")

    out_path.write_bytes(content)
    digest = sha256_bytes(content)

    record = DocumentVersion(
        doc_id=doc_id,
        jurisdiction=jurisdiction,
        title=title,
        source_url=source_url,
        local_path=str(out_path.as_posix()),
        downloaded_at=_utc_now_iso(),
        sha256=digest,
        effective_date=effective_date,
        amendment_date=amendment_date,
        supersedes=supersedes,
        superseded_by=superseded_by,
    )

    manifest = _read_json(manifest_path)
    _upsert_document(manifest, record)
    _write_json(manifest_path, manifest)
    return record


def list_documents(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = _read_json(manifest_path)
    return list(manifest.get("documents", []))

