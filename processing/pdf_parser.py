import fitz
import re
from pathlib import Path
from dataclasses import dataclass, field

# ── General-purpose hierarchy detector ──────────────────────────────────────
# Matches patterns like:
#   Article 1, Article 1.1, Section 2, Clause 3.1.2
#   1.1, 1.1.1, (a), (b)(i), 1.1(a), 1.1(b)(ii)
# WITHOUT hardcoding specific keywords

SECTION_PATTERN = re.compile(
    r"""
    (?:^|\n)                          # start of line
    (?P<heading>
        (?:
            (?:Article|Section|Clause|Part|Schedule|Annex|Appendix)  
            \s+
        )?                            # optional keyword prefix
        (?:
            \d+(?:\.\d+)*             # numeric: 1, 1.1, 1.1.2
            (?:\([a-zA-Z0-9]+\))*     # optional: (a), (b)(i)
            |                         
            \([a-zA-Z0-9]+\)          # pure lettered: (a), (b)
            (?:\([a-zA-Z0-9]+\))*     # nested: (a)(i)
        )
        [^\n]{0,120}                  # rest of heading line, capped at 120 chars
    )
    """,
    re.VERBOSE | re.MULTILINE | re.IGNORECASE
)

# Figures stay as metadata, never become sections
FIGURE_PATTERN = re.compile(
    r"(?:Figure|Image|Img|Table|Exhibit)\s+[\d.]+[^\n]*",
    re.IGNORECASE
)

# Semantic completeness — ends without proper punctuation
INCOMPLETE_SENTENCE_PATTERN = re.compile(r"[^.!?:;)\]]\s*$")


@dataclass
class LegalSection:
    section_id: int
    heading: str
    text: str
    depth: int                        # 1=top, 2=sub, 3=sub-sub etc.
    parent_id: int | None
    numeric_id: str | None            # e.g "1.1", "1.1(a)"
    figures: list[str]                # figure refs found IN this section
    word_count: int
    char_count: int
    semantic_complete: bool


def infer_depth(heading: str) -> tuple[int, str | None]:
    """
    Infers hierarchy depth from the heading text alone.
    No hardcoded keywords needed.

    Returns (depth, numeric_id)

    Examples:
        "Article 1"       → (1, "1")
        "Clause 1.1"      → (2, "1.1")
        "1.1.2"           → (3, "1.1.2")
        "(a)"             → (3, "(a)")
        "1.1(b)"          → (3, "1.1(b)")
        "1.1(b)(i)"       → (4, "1.1(b)(i)")
    """
    # Extract numeric/lettered identifier from heading
    id_match = re.search(
        r"(\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*|\([a-zA-Z0-9]+\)(?:\([a-zA-Z0-9]+\))*)",
        heading
    )
    if not id_match:
        return (1, None)

    numeric_id = id_match.group(1)

    # Count structural levels:
    # dots → numeric nesting depth
    # brackets → lettered sub-levels
    dot_depth = numeric_id.count(".") + 1
    bracket_depth = len(re.findall(r"\([a-zA-Z0-9]+\)", numeric_id))
    depth = dot_depth + bracket_depth

    return (depth, numeric_id)


def check_semantic_completeness(text: str) -> bool:
    return not bool(INCOMPLETE_SENTENCE_PATTERN.search(text.strip()))


def stream_pages(file_path: Path):
    """
    Generator — yields one page's text at a time.
    Never holds the full document in memory.
    """
    with fitz.open(file_path) as doc:
        for page in doc:
            yield page.get_text()


def extract_legal_sections(file_path: str | Path) -> list[LegalSection]:
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected .pdf, got: {file_path.suffix}")

    # ── Stream pages, carry a small overlap buffer ───────────────────────────
    # Why overlap? A section heading can be split across a page boundary:
    #   Page 4 ends: "...damages.\nClause"
    #   Page 5 starts: "1.1 - Indemnity\nThe party..."
    # Without overlap, "Clause 1.1" is never matched.
    # We carry the last 300 chars of the previous page into the next chunk.

    OVERLAP = 300
    sections: list[LegalSection] = []
    section_id = 0
    tail = ""                         # overlap carry from previous page
    depth_stack: list[tuple[int,int]] = []  # (depth, section_id) for parent tracking

    for page_text in stream_pages(file_path):
        chunk = tail + page_text
        boundaries = [
            (m.start(), m.group("heading").strip())
            for m in SECTION_PATTERN.finditer(chunk)
        ]

        for i, (start, heading) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(chunk) - OVERLAP
            if end <= start:
                continue

            text = chunk[start:end].strip()
            if not text or len(text.split()) < 3:   # skip noise matches
                continue

            depth, numeric_id = infer_depth(heading)

            # ── Parent resolution via depth stack ────────────────────────────
            # Pop stack until we find a section shallower than current depth
            while depth_stack and depth_stack[-1][0] >= depth:
                depth_stack.pop()
            parent_id = depth_stack[-1][1] if depth_stack else None
            depth_stack.append((depth, section_id))

            # ── Extract figures as metadata, not sections ─────────────────────
            figures = FIGURE_PATTERN.findall(text)
            # Remove figure lines from the section text itself
            clean_text = FIGURE_PATTERN.sub("", text).strip()

            sections.append(LegalSection(
                section_id=section_id,
                heading=heading,
                text=clean_text,
                depth=depth,
                parent_id=parent_id,
                numeric_id=numeric_id,
                figures=figures,
                word_count=len(clean_text.split()),
                char_count=len(clean_text),
                semantic_complete=check_semantic_completeness(clean_text),
            ))
            section_id += 1

        # Carry last OVERLAP chars into next page to catch boundary splits
        tail = page_text[-OVERLAP:]

    incomplete = [s for s in sections if not s.semantic_complete]
    if incomplete:
        print(f"[WARNING] {len(incomplete)} section(s) may be semantically incomplete:")
        for s in incomplete:
            print(f"  → id={s.section_id} depth={s.depth} | {s.heading[:60]}")

    return sections