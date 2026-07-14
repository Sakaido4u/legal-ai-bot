import fitz
import re
from pathlib import Path
from dataclasses import dataclass

# General-purpose hierarchy detector.
# Matches patterns like:
#   Article 1, Article 1.1, Section 2, Clause 3.1.2
#   1.1, 1.1.1, (a), (b)(i), 1.1(a), 1.1(b)(ii)
# WITHOUT hardcoding specific keywords.
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
    re.VERBOSE | re.MULTILINE | re.IGNORECASE,
)

# Figures stay as metadata, never become sections.
FIGURE_PATTERN = re.compile(
    r"(?:Figure|Image|Img|Table|Exhibit)\s+[\d.]+[^\n]*",
    re.IGNORECASE,
)

# Semantic completeness - ends without proper punctuation.
INCOMPLETE_SENTENCE_PATTERN = re.compile(r"[^.!?:;)\]]\s*$")


@dataclass
class LegalSection:
    section_id: int
    heading: str
    text: str
    depth: int
    parent_id: int | None
    numeric_id: str | None
    figures: list[str]
    word_count: int
    char_count: int
    semantic_complete: bool


def infer_depth(heading: str) -> tuple[int, str | None]:
    """
    Infers hierarchy depth from the heading text alone.
    No hardcoded keywords needed.

    Returns (depth, numeric_id)

    Examples:
        "Article 1"       -> (1, "1")
        "Clause 1.1"      -> (2, "1.1")
        "1.1.2"           -> (3, "1.1.2")
        "(a)"             -> (3, "(a)")
        "1.1(b)"          -> (3, "1.1(b)")
        "1.1(b)(i)"       -> (4, "1.1(b)(i)")
    """
    id_match = re.search(
        r"(\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*|\([a-zA-Z0-9]+\)(?:\([a-zA-Z0-9]+\))*)",
        heading,
    )
    if not id_match:
        return (1, None)

    numeric_id = id_match.group(1)

    # dots -> numeric nesting depth; brackets -> lettered sub-levels.
    dot_depth = numeric_id.count(".") + 1
    bracket_depth = len(re.findall(r"\([a-zA-Z0-9]+\)", numeric_id))
    depth = dot_depth + bracket_depth

    return (depth, numeric_id)


def check_semantic_completeness(text: str) -> bool:
    return not bool(INCOMPLETE_SENTENCE_PATTERN.search(text.strip()))


def stream_pages(file_path: Path):
    """
    Generator - yields one page's text at a time.
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

    with fitz.open(file_path) as doc:
        total_pages = doc.page_count

    OVERLAP = 300
    sections: list[LegalSection] = []
    section_id = 0
    tail = ""
    depth_stack: list[tuple[int, int]] = []

    for page_num, page_text in enumerate(stream_pages(file_path)):
        is_last_page = page_num == total_pages - 1
        chunk = tail + page_text
        cutoff = len(chunk) - OVERLAP

        boundaries = [
            (m.start(), m.group("heading").strip())
            for m in SECTION_PATTERN.finditer(chunk)
        ]

        # Drop headings that start inside the trailing overlap zone. They will
        # be re-detected in full once `tail` carries them into the next page.
        if not is_last_page:
            boundaries = [
                (start, heading)
                for start, heading in boundaries
                if start < cutoff
            ]

        for i, (start, heading) in enumerate(boundaries):
            if i + 1 < len(boundaries):
                end = boundaries[i + 1][0]
            else:
                # Last page has no next page to hand remaining text off to.
                end = len(chunk) if is_last_page else cutoff

            if end <= start:
                continue

            text = chunk[start:end].strip()
            if not text or len(text.split()) < 3:
                continue

            depth, numeric_id = infer_depth(heading)

            while depth_stack and depth_stack[-1][0] >= depth:
                depth_stack.pop()
            parent_id = depth_stack[-1][1] if depth_stack else None
            depth_stack.append((depth, section_id))

            figures = FIGURE_PATTERN.findall(text)
            clean_text = FIGURE_PATTERN.sub("", text).strip()

            sections.append(
                LegalSection(
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
                )
            )
            section_id += 1

        tail = page_text[-OVERLAP:] if not is_last_page else ""

    incomplete = [s for s in sections if not s.semantic_complete]
    if incomplete:
        print(f"[WARNING] {len(incomplete)} section(s) may be semantically incomplete:")
        for s in incomplete:
            print(f"  -> id={s.section_id} depth={s.depth} | {s.heading[:60]}")

    return sections
