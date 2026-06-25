## documents/

This folder stores **downloaded legal source documents** (GDPR / DPDP / CCPA) so ingestion is reproducible.

- **Download + version tracking**: run `python scripts/fetch_regulations.py`
- **Version metadata**: `documents/manifest.json` (sha256, dates, supersession links)
- **Ingest into index**: run `python scripts/ingest.py --pdf <path>` or point `data/corpus_seeds.json` to these files and run `python scripts/build_corpus_index.py`

