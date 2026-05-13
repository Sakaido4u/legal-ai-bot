from pathlib import Path

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_PATH        = BASE_DIR / "data" / "raw"
PROCESSED_DATA_PATH  = BASE_DIR / "data" / "processed"
LOG_PATH             = BASE_DIR / "logs"

# ─────────────────────────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────────────────────────

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100

# ─────────────────────────────────────────────────────────────
# WEB SCRAPER
# ─────────────────────────────────────────────────────────────

REQUEST_TIMEOUT      = 15       # seconds per request
REQUEST_RETRIES      = 3        # attempts before giving up
REQUEST_BACKOFF      = 2.0      # exponential base — 2s, 4s, 8s
RATE_LIMIT_SECONDS   = 1.5      # wait between URLs in batch

# ─────────────────────────────────────────────────────────────
# PDF PROCESSOR
# ─────────────────────────────────────────────────────────────

PAGE_OVERLAP_CHARS   = 300      # carry-over between pages to catch boundary splits

# ─────────────────────────────────────────────────────────────
# SECTION EXTRACTOR (shared by PDF + web)
# ─────────────────────────────────────────────────────────────

MIN_SECTION_WORDS    = 3        # skip sections with fewer words than this

# ─────────────────────────────────────────────────────────────
# DIRECTORY BOOTSTRAP
# ─────────────────────────────────────────────────────────────

for _path in (RAW_DATA_PATH, PROCESSED_DATA_PATH, LOG_PATH):
    _path.mkdir(parents=True, exist_ok=True)