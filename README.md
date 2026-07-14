# Legal AI Regulatory Risk Intelligence Engine

> AI-powered platform for **cross-jurisdictional regulatory document analysis**, compliance intelligence, and legal risk assessment using Retrieval-Augmented Generation (RAG), semantic search, and Large Language Models (LLMs).

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-Language-3178C6?style=for-the-badge&logo=typescript)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-Optional-412991?style=for-the-badge&logo=openai)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20DB-orange?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Document%20Store-336791?style=for-the-badge&logo=postgresql)
![MIT License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)

---

## Overview

Legal and compliance teams spend hours manually reviewing statutes, frameworks, and policy documents across jurisdictions.

This platform turns that workflow into a **product-feature compliance copilot**. It combines:

- **Retrieval-Augmented Generation (RAG)**
- **Semantic search** with FAISS
- **Citation-bound LLM answers** (Ollama, OpenAI, or safe template mode)
- **Cross-jurisdiction comparison** for GDPR, India’s DPDP Act, and CCPA/CPRA
- **Heuristic regulatory risk scoring** with explainable factors

Upload or ingest regulatory PDFs and HTML sources, then ask natural-language questions about product features and receive grounded answers with citations, risk heatmap signals, and jurisdiction divergence notes.

> **Not legal advice.** Outputs are research assist tools for review by qualified counsel.

---

## Features

- Upload and analyze PDF legal / regulatory documents
- Hierarchy-aware legal PDF parsing and web scraping
- Jurisdiction-aware FAISS vector indexing (GDPR · DPDP · CCPA)
- Semantic retrieval with similarity floor + MMR re-ranking
- Citation-masked LLM generation (invalid / missing citations → refuse)
- Regulatory risk scoring and cross-jurisdiction stance comparison
- Unified ingestion CLI (PDF / URL / seed corpus)
- Retrieval benchmarks and embedding fine-tune pipeline
- Optional local LLM via **Ollama** (`compliance-llm`) or **OpenAI**
- PostgreSQL metadata store for documents, sections, chunks, and analysis logs
- React + TypeScript frontend (LexAI UI)
- FastAPI OpenAPI docs at `/docs`

---

## System Architecture

```text
                         ┌────────────────────┐
                         │       User         │
                         └─────────┬──────────┘
                                   │
                                   ▼
                      React + TypeScript Frontend
                            (LexAI · Vite)
                                   │
                                   ▼
                           FastAPI Backend
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   Document Processing      Embedding + FAISS          Query / Risk API
   (PDF / Web / Upload)     (Sentence Transformers)    (RAG pipeline)
          │                        │                        │
          ▼                        ▼                        ▼
   Legal-hierarchy chunks ──► Vector index ◄────────── Query embedding
                                   │
                                   ▼
                        Relevant passage retrieval
                                   │
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
               Risk scorer   Cross-jurisdiction   Citation LLM
                                             (Ollama / OpenAI / template)
                                   │
                                   ▼
              Citation-backed answer + risk heatmap + stance matrix
                                   │
                                   ▼
                         PostgreSQL (documents / logs)
```

---

## Tech Stack

| Layer | Stack |
|-------|--------|
| **Frontend** | React, TypeScript, Tailwind CSS, Vite |
| **Backend** | FastAPI, Uvicorn, Pydantic Settings |
| **ML / RAG** | Sentence Transformers, FAISS, custom retrieval + citation pipeline |
| **LLM** | Ollama (default local), OpenAI (optional), template fallback |
| **Document processing** | PyMuPDF, BeautifulSoup |
| **Database** | PostgreSQL + SQLAlchemy |
| **Scripts** | Corpus build, ingest, benchmarks, Ollama setup, embedding fine-tune |

---

## Project Structure

```text
legal-ai-bot/
├── frontend/                 # LexAI React + TypeScript UI
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── src/                      # Python packages (PYTHONPATH=src)
│   ├── backend/              # FastAPI app, routes, RAG service
│   ├── ml/                   # Embeddings, FAISS, retrieval, LLM, eval
│   ├── database/             # SQLAlchemy models + session
│   └── services/             # Document / query / risk services
│
├── processing/               # PDF parser, web scraper, document helpers
├── scripts/                  # Build index, ingest, benchmarks, setup
├── documents/                # Seeded GDPR / DPDP / CCPA source snapshots
├── data/                     # Corpus seeds + uploads
├── ollama/                   # Custom Modelfile for compliance-llm
├── config/                   # Shared path / processing settings
├── requirements.txt
├── pyproject.toml
├── .env.example
├── LICENSE
└── README.md
```

---

## How It Works

1. **Ingest or upload** — PDF statutes, web pages, or seeded corpus
2. **Parse** — hierarchy-aware section extraction
3. **Chunk** — legal-boundary-aware chunking for retrieval
4. **Embed** — Sentence Transformers → dense vectors
5. **Index** — FAISS indexes partitioned by jurisdiction
6. **Query** — natural language + product feature + jurisdiction list
7. **Retrieve** — similarity floor + MMR diversification
8. **Score & compare** — risk factors + cross-jurisdiction stance
9. **Generate** — citation-bound LLM answer (or refuse if evidence is weak)

---

## Installation

### Clone

```bash
git clone https://github.com/Sakaido4u/legal-ai-bot.git
cd legal-ai-bot
```

### Backend

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
# or: pip install -e .
```

Copy environment template:

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

Build the vector index (first run):

```bash
set PYTHONPATH=src              # Windows PowerShell: $env:PYTHONPATH="src"
python scripts/build_corpus_index.py
```

Optional — local Ollama LLM:

```bash
python scripts/setup_ollama.py
# then set in .env:
# COMPLIANCE_LLM_PROVIDER=ollama
# COMPLIANCE_LLM_MODEL=compliance-llm
```

PostgreSQL (required for document upload + persistence APIs):

- Create database `legal_ai`
- Set `COMPLIANCE_DATABASE_URL` in `.env`

Run API:

```bash
$env:PYTHONPATH="src"   # PowerShell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

### Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Frontend defaults to http://127.0.0.1:3000 (see `vite.config.ts`).

Ensure backend CORS includes your frontend origin, for example:

```env
COMPLIANCE_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

---

## Environment Variables

See `.env.example`. Important keys:

```env
COMPLIANCE_INDEX_DIR=vector_store/regulatory
COMPLIANCE_USE_DEMO_INDEX=false
COMPLIANCE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

COMPLIANCE_LLM_PROVIDER=ollama          # template | ollama | openai
COMPLIANCE_LLM_MODEL=compliance-llm
COMPLIANCE_OLLAMA_BASE_URL=http://127.0.0.1:11434
# COMPLIANCE_LLM_API_KEY=sk-...         # when using openai

COMPLIANCE_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/legal_ai
COMPLIANCE_UPLOAD_DIR=data/uploads
COMPLIANCE_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Frontend (`frontend/.env`):

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_ENV=development
```

---

## Core API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service map |
| `GET` | `/health` | Index + LLM / Ollama status |
| `POST` | `/v1/compliance/analyze` | Legacy compliance analyze |
| `GET` | `/v1/compliance/jurisdictions` | Supported jurisdictions |
| `POST` | `/documents/upload` | Upload PDF → parse → Postgres → reindex |
| `GET` | `/documents` | List documents |
| `GET` | `/documents/{id}` | Document detail |
| `DELETE` | `/documents/{id}` | Delete + rebuild index |
| `POST` | `/legal_query` | Grounded legal query |
| `POST` | `/risk_analysis` | Risk-focused analysis |

Interactive OpenAPI: **http://127.0.0.1:8000/docs**

---

## Useful Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_corpus_index.py` | Build FAISS index from `data/corpus_seeds.json` |
| `scripts/ingest.py` | Ingest PDF / URL / seed file into vector store |
| `scripts/setup_ollama.py` | Pull llama3.2 + create `compliance-llm` |
| `scripts/run_benchmarks.py` | Retrieval quality smoke benchmarks |
| `scripts/finetune_embeddings.py` | Domain-adapt embeddings + rebuild index |
| `scripts/demo_analyze.py` | CLI compliance demo |
| `scripts/fetch_regulations.py` | Fetch / snapshot regulation sources |

---

## Example Questions

- What consent is required for children’s personal data under DPDP vs GDPR?
- Can we process biometric data for login, and how do GDPR Art. 9 and CCPA interact?
- What are erasure / deletion rights across GDPR, DPDP, and CCPA?
- Flag jurisdictions with divergent stances for location tracking.
- Summarize reporting or notice obligations relevant to this product feature.

---

## Use Cases

| Audience | Examples |
|----------|----------|
| **SaaS / product teams** | Pre-ship compliance checks across GDPR, DPDP, CCPA |
| **Privacy / legal ops** | Fast cited research for feature memos |
| **Consultancies** | White-label regulatory Q&A assist |
| **Students / researchers** | Cross-jurisdiction RAG and evaluation experiments |

---

## Performance Goals

| Metric | Target |
|--------|--------|
| Semantic retrieval | Sub-second against local FAISS |
| Index build (seed corpus) | Minutes on CPU (first model download longer) |
| LLM answer (Ollama / API) | Typically a few seconds, hardware-dependent |
| Citation discipline | Invalid citation IDs refused |

---

## Team

| Role | Person |
|------|--------|
| Core ML Lead | **Avaneesh Bukenkere** |
| Core Frontend | **Amogh V N** |
| Core Backend | **Deeptanshu Pandey** |
| Core ML (Fine-tuning) | **Adithya V** |

Computer Science Engineering · AI / ML · Full-stack systems

Repository: [github.com/Sakaido4u/legal-ai-bot](https://github.com/Sakaido4u/legal-ai-bot)

---

## Disclaimer

This software is for **education, research, and demonstration**.

It **does not provide legal advice** and is **not** a substitute for advice from qualified legal professionals. Always validate outputs against primary instruments and counsel review.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request against `main`

Please keep PRs focused (ML · backend · frontend · docs) and include how to test.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
