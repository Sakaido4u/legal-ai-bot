"""Unit tests for citation evidence gate, sentence chunking, and query decomposition."""

from __future__ import annotations

from ml.chunking import chunk_text, split_sentences, trim_orphaned_edges
from ml.evidence import assess_evidence
from ml.legal_chunking import article_key_from_text, group_primary_legal_units, sections_to_chunks
from ml.query_expand import decompose_query
from ml.schemas import Jurisdiction, RetrievedPassage


class _Sec:
    def __init__(self, heading: str, text: str) -> None:
        self.heading = heading
        self.text = text


def test_chunk_text_does_not_break_mid_word():
    text = (
        "Processing shall be lawful only if and to the extent that at least one of the following applies. "
        "The data subject has given consent to the processing of his or her personal data for one or more specific purposes. "
        "Processing is necessary for compliance with a legal obligation to which the controller is subject."
    )
    chunks = chunk_text(
        text=text,
        jurisdiction=Jurisdiction.GDPR,
        source_label="GDPR test",
        heading="Article 6",
        chunk_size=160,
        chunk_overlap=40,
    )
    assert chunks
    for c in chunks:
        assert not c.text[0].islower(), f"mid-word/mid-sentence start: {c.text[:40]!r}"
        # No partial words from fixed-window slicing (spaces preserved around joins).
        assert "  " not in c.text


def test_trim_orphaned_edges_drops_leading_lowercase_fragment():
    cleaned = trim_orphaned_edges(
        "de the personal data public and is obliged. The controller shall erase personal data."
    )
    assert cleaned.startswith("The controller")


def test_group_primary_units_keeps_articles():
    sections = [
        _Sec("4.5.2016", "EN Official Journal"),
        _Sec("Article 5", "Article 5\n1. Personal data shall be processed lawfully, fairly and in a transparent manner."),
        _Sec("(a)", "collected for specified, explicit and legitimate purposes."),
        _Sec("Article 28", "Article 28\n1. Where processing is carried out on behalf of a controller."),
        _Sec("Article 44", "Article 44\nAny transfer of personal data to a third country shall take place only under conditions."),
    ]
    units = group_primary_legal_units(sections)
    headings = [h for h, _ in units]
    assert "Article 5" in headings
    assert "Article 28" in headings
    assert "Article 44" in headings
    assert all(not (h or "").startswith("4.5") for h, _ in units)


def test_sections_to_chunks_sentence_aware_for_long_article():
    long_body = " ".join(
        f"Sentence number {i} states an obligation the controller shall meet regarding personal data."
        for i in range(40)
    )
    chunks = sections_to_chunks(
        [_Sec("Article 46", f"Article 46\n{long_body}")],
        jurisdiction=Jurisdiction.GDPR,
        source_label="GDPR",
        max_section_chars=200,
        chunk_size=220,
        chunk_overlap=40,
    )
    assert len(chunks) >= 2
    for c in chunks:
        assert not c.text[0].islower()


def test_assess_evidence_insufficient_when_empty():
    ev = assess_evidence([])
    assert ev.sufficient is False
    assert ev.low_confidence is False


def test_assess_evidence_low_confidence_flag():
    passages = [
        RetrievedPassage(
            chunk_id="a",
            jurisdiction=Jurisdiction.GDPR,
            source_label="GDPR | Article 5",
            heading="Article 5",
            text="Personal data shall be kept for no longer than necessary.",
            similarity=0.41,
        )
    ]
    ev = assess_evidence(passages, min_score=0.22, confidence_floor=0.50)
    assert ev.sufficient is True
    assert ev.low_confidence is True


def test_decompose_query_adds_transfer_and_dpa_aspects():
    q = (
        "We store EU user data in the US, retain it for 5 years, share with advertising partners, "
        "and do not have a Data Processing Agreement with our cloud hosting provider. GDPR compliant?"
    )
    parts = decompose_query(q)
    assert parts[0] == q
    blob = " ".join(parts).lower()
    assert "transfer" in blob or "scc" in blob
    assert "retention" in blob or "storage" in blob
    assert "processor" in blob or "article 28" in blob


def test_article_key_from_text():
    assert article_key_from_text("GDPR | Article 28", "Where processing is carried out") == "Article 28"
    assert article_key_from_text("no statute here") is None


def test_split_sentences_basic():
    parts = split_sentences("One ends. Two ends! Three ends?")
    assert len(parts) == 3
