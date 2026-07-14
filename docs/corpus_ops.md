# Corpus, index, and Ollama ops

## Current state (as of Phase 4)

| Layer | What exists today | What is NOT migrated |
|-------|-------------------|----------------------|
| **Regulatory corpus vectors** | Local **FAISS** under `vector_store/regulatory` (or fine-tuned sibling dirs) | Vectors themselves stay on disk — intentional for speed |
| **Index metadata (manifest)** | `manifest.json` / ingest stats beside the FAISS files | Not copied into Postgres |
| **Uploaded user PDFs** | Text + chunks + `vector_reference` in **Postgres**; embeddings appended into the running FAISS store at upload time | Already Postgres for relational metadata |
| **Analysis history** | `compliance_analyses` in Postgres | — |
| **LLM** | `COMPLIANCE_LLM_PROVIDER=ollama` default; falls back to **template** if Ollama is down; **openai** optional with API key | No separate “cloud-only” path beyond OpenAI |

**Postgres index-metadata migration:** not done. Moving FAISS chunk manifests into Postgres would be a **schema + reindex project**, not a small migration. Confirm before we do it — for the course demo, disk FAISS + Postgres document/chunk rows is enough.

## Build / rebuild the full local corpus index

From repo root (after `pip install -e .`):

```bash
python scripts/build_corpus_index.py
# optional:
python scripts/build_corpus_index.py --seeds data/corpus_seeds.json --output vector_store/regulatory
```

Then set:

```env
COMPLIANCE_INDEX_DIR=vector_store/regulatory
COMPLIANCE_USE_DEMO_INDEX=false
```

Related helpers:

- `python scripts/ingest.py` — one-off PDF/URL ingest
- `python scripts/fetch_regulations.py` — refresh seed sources
- `python scripts/finetune_embeddings.py` — optional embedding fine-tune
- `python scripts/setup_ollama.py` — pull/create local `compliance-llm` model

Also apply DB migrations:

```bash
python -m alembic upgrade head
```

## Confirm Ollama end-to-end

1. Install & start [Ollama](https://ollama.com).
2. `python scripts/setup_ollama.py` (or `ollama pull` the configured model).
3. `.env`:
   ```env
   COMPLIANCE_LLM_PROVIDER=ollama
   COMPLIANCE_LLM_MODEL=compliance-llm
   COMPLIANCE_OLLAMA_BASE_URL=http://127.0.0.1:11434
   ```
4. Start API → `GET /health` should show `"llm_provider":"ollama"` and `ollama.status` = `ok` (else `degraded` with template still usable for some paths).
5. Run Analyze from the UI; answer should come from Ollama when healthy (check server logs).

Template mode remains the safe offline fallback; set `COMPLIANCE_LLM_PROVIDER=template` to force it.
