import re
import time
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# DATA MODEL
# ─────────────────────────────────────────────────────────────

@dataclass
class WebSection:
    section_id: int
    heading: str
    text: str
    level: int                        # h1=1 … h6=6
    depth: int                        # structural depth in THIS document
    parent_id: int | None             # mirrors LegalSection.parent_id
    source_url: str
    figures: list[str] = field(default_factory=list)   # img alt texts found in section
    word_count: int = 0
    char_count: int = 0
    semantic_complete: bool = True


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

JUNK_TAGS = [
    "script", "style", "nav", "footer",
    "header", "aside", "form", "noscript",
    "iframe", "svg", "button", "menu",
]

HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]

WHITESPACE_PATTERN = re.compile(r"\s+")
INCOMPLETE_SENTENCE_PATTERN = re.compile(r"[^.!?:;)\]]\s*$")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────

def validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# HTTP FETCHING — with retries
# ─────────────────────────────────────────────────────────────

def fetch_html(
    url: str,
    retries: int = 3,
    backoff: float = 2.0,
    timeout: int = 15,
) -> str:
    """
    Fetches HTML with exponential backoff on failure.
    backoff=2.0 means: wait 2s, then 4s, then 8s between retries.
    """
    if not validate_url(url):
        raise ValueError(f"Invalid URL: {url}")

    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            last_error = e
            wait = backoff ** attempt          # 1s, 2s, 4s
            logger.warning(
                f"Attempt {attempt + 1}/{retries} failed for {url}: {e}. "
                f"Retrying in {wait:.1f}s..."
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Failed to fetch {url} after {retries} attempts: {last_error}"
    )


# ─────────────────────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def check_semantic_completeness(text: str) -> bool:
    return not bool(INCOMPLETE_SENTENCE_PATTERN.search(text.strip()))


# ─────────────────────────────────────────────────────────────
# STRUCTURED SECTION EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_structured_sections(
    html: str,
    source_url: str,
) -> list[WebSection]:

    soup = BeautifulSoup(html, "html.parser")

    for tag in JUNK_TAGS:
        for element in soup.find_all(tag):
            element.decompose()

    sections: list[WebSection] = []
    section_id = 0
    current_heading = "Introduction"
    current_level = 1
    buffer: list[str] = []
    figures_buffer: list[str] = []

    # depth stack mirrors what we built for legal sections
    # stores (level, section_id) to resolve parent_id
    depth_stack: list[tuple[int, int]] = []

    def flush_buffer():
        """Saves buffered text as a WebSection and resets buffer."""
        nonlocal section_id

        if not buffer:
            return

        text = clean_text(" ".join(buffer))
        if not text or len(text.split()) < 3:   # skip noise
            buffer.clear()
            figures_buffer.clear()
            return

        # ── Parent resolution (same logic as legal extractor) ────────────
        while depth_stack and depth_stack[-1][0] >= current_level:
            depth_stack.pop()
        parent_id = depth_stack[-1][1] if depth_stack else None
        depth = len(depth_stack) + 1
        depth_stack.append((current_level, section_id))

        sections.append(WebSection(
            section_id=section_id,
            heading=current_heading,
            text=text,
            level=current_level,
            depth=depth,
            parent_id=parent_id,
            source_url=source_url,
            figures=list(figures_buffer),
            word_count=len(text.split()),
            char_count=len(text),
            semantic_complete=check_semantic_completeness(text),
        ))

        section_id += 1
        buffer.clear()
        figures_buffer.clear()

    # Traverse in true document order using recursion-safe .descendants
    # This avoids find_all(list) ordering issues across tag types
    for element in soup.find_all(True):

        if element.name in HEADING_TAGS:
            flush_buffer()
            current_heading = clean_text(element.get_text(" "))
            current_level = int(element.name[1])

        elif element.name == "img":
            # Capture figures as metadata, not text content
            alt = element.get("alt", "").strip()
            if alt:
                figures_buffer.append(alt)

        elif element.name in ("p", "li", "td", "blockquote"):
            text = clean_text(element.get_text(" "))
            if text:
                buffer.append(text)

    flush_buffer()   # catch final section

    incomplete = [s for s in sections if not s.semantic_complete]
    if incomplete:
        logger.warning(
            f"{len(incomplete)} section(s) may be semantically incomplete "
            f"in {source_url}"
        )

    return sections


# ─────────────────────────────────────────────────────────────
# BATCH PIPELINE — mirrors legal extractor's structure
# ─────────────────────────────────────────────────────────────

def extract_from_urls(
    urls: list[str],
    rate_limit_seconds: float = 1.5,
) -> list[WebSection]:
    """
    Processes multiple URLs with rate limiting between requests.
    Returns flat list of all WebSections across all URLs.
    """
    all_sections: list[WebSection] = []

    for i, url in enumerate(urls):
        try:
            logger.info(f"[{i+1}/{len(urls)}] Fetching: {url}")
            html = fetch_html(url)
            sections = extract_structured_sections(html, url)
            all_sections.extend(sections)
            logger.info(f"  → {len(sections)} sections extracted")

        except Exception as e:
            logger.error(f"  → Skipping {url}: {e}")

        # Rate limit between requests — not after the last one
        if i < len(urls) - 1:
            time.sleep(rate_limit_seconds)

    return all_sections


# single URL convenience wrapper
def extract_text_from_url(url: str) -> list[WebSection]:
    html = fetch_html(url)
    return extract_structured_sections(html, url)


# ─────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    urls = [
        "https://gdpr-info.eu/art-17-gdpr/",
        "https://gdpr-info.eu/art-18-gdpr/",
    ]

    sections = extract_from_urls(urls, rate_limit_seconds=1.5)

    print(f"\nExtracted {len(sections)} sections\n")

    for section in sections[:3]:
        print("=" * 80)
        print(f"Heading  : {section.heading}")
        print(f"Level    : {section.level}  |  Depth: {section.depth}  |  Parent: {section.parent_id}")
        print(f"Words    : {section.word_count}  |  Complete: {section.semantic_complete}")
        print(f"Figures  : {section.figures}")
        print()
        print(section.text[:500])
        print()