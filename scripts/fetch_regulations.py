#!/usr/bin/env python3
"""
Download canonical GDPR / DPDP / CCPA sources into ./documents and write version metadata.

This keeps the repository ingestion reproducible:
- documents are stored locally
- documents/manifest.json tracks sha256 + dates + supersession links
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from processing.document_store import download_document  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _download_with_fallbacks(*, urls: list[str], **kwargs):
    last_err: Exception | None = None
    for u in urls:
        try:
            return download_document(source_url=u, **kwargs)
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("Failed download from %s (%s)", u, e)
    assert last_err is not None
    raise last_err


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GDPR/DPDP/CCPA documents into ./documents/")
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=ROOT / "documents",
        help="Where to store downloaded documents",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "documents" / "manifest.json",
        help="Manifest path for version tracking",
    )
    args = parser.parse_args()

    docs_dir: Path = args.documents_dir
    manifest: Path = args.manifest

    # NOTE: URLs chosen to be stable + official where possible.
    # If an upstream URL changes, the sha256 in manifest will show a divergence.
    records = []

    # GDPR (Regulation (EU) 2016/679) – EUR-Lex PDF
    records.append(
        _download_with_fallbacks(
            doc_id="gdpr-2016-679-eurlex-pdf",
            jurisdiction="GDPR",
            title="Regulation (EU) 2016/679 (GDPR) — snapshot",
            urls=[
                # UK legislation site hosts the adopted EUR-Lex PDF and is often more accessible.
                "https://www.legislation.gov.uk/eur/2016/679/pdfs/eur_20160679_adopted_en.pdf",
                "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679&qid=1692214269082",
            ],
            target_dir=docs_dir / "gdpr",
            filename="gdpr_2016_679.pdf",
            manifest_path=manifest,
            effective_date="2018-05-25",
            min_bytes=1024,
        )
    )

    # DPDP (India) – Digital Personal Data Protection Act, 2023.
    # Commonly distributed via India Code (Ministry of Law & Justice). PDF endpoint may vary.
    records.append(
        _download_with_fallbacks(
            doc_id="dpdp-2023-indiacode-pdf",
            jurisdiction="DPDP",
            title="Digital Personal Data Protection Act, 2023 — India Code PDF",
            urls=[
                "https://www.indiacode.nic.in/bitstream/123456789/20036/1/digital_personal_data_protection_act_2023.pdf",
                "https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf",
                "https://egazette.gov.in/WriteReadData/2023/248045.pdf",
            ],
            target_dir=docs_dir / "dpdp",
            filename="dpdp_act_2023.pdf",
            manifest_path=manifest,
            amendment_date=None,
        )
    )

    # CCPA / CPRA (California) – store OAG overview page as an HTML snapshot for reproducibility.
    records.append(
        download_document(
            doc_id="ccpa-oag-html",
            jurisdiction="CCPA",
            title="California DOJ / OAG CCPA overview — HTML snapshot",
            source_url="https://oag.ca.gov/privacy/ccpa",
            target_dir=docs_dir / "ccpa",
            filename="ccpa_oag_snapshot.html",
            manifest_path=manifest,
        )
    )

    for r in records:
        logger.info("Downloaded %s -> %s (sha256=%s)", r.doc_id, r.local_path, r.sha256[:12])

    logger.info("Done. Manifest updated at %s", manifest)


if __name__ == "__main__":
    main()

