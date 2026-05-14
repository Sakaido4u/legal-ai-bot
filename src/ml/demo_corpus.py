from __future__ import annotations

from .schemas import ChunkRecord, Jurisdiction


def demo_chunks() -> list[ChunkRecord]:
    """
    Tiny synthetic corpus so the API is testable before real ingestion.
    Not legal advice - placeholders for pipeline / UI wiring.
    """
    return [
        ChunkRecord(
            chunk_id="demo-gdpr-1",
            jurisdiction=Jurisdiction.GDPR,
            source_label="GDPR Art. 9 (demo excerpt)",
            heading="Special categories",
            text=(
                "Processing of personal data revealing racial or ethnic origin, political opinions, "
                "religious or philosophical beliefs, or trade union membership, and the processing of "
                "genetic data, biometric data for the purpose of uniquely identifying a natural person, "
                "data concerning health or data concerning a natural person's sex life or sexual orientation "
                "shall be prohibited unless specific conditions apply."
            ),
        ),
        ChunkRecord(
            chunk_id="demo-dpdp-1",
            jurisdiction=Jurisdiction.DPDP,
            source_label="DPDP Act - sensitive personal data (demo excerpt)",
            heading="Sensitive personal data",
            text=(
                "Certain classes of personal data may be processed with explicit consent and additional "
                "safeguards. The law contemplates permitted processing where necessary for clear purposes "
                "subject to notice, purpose limitation, and security measures."
            ),
        ),
        ChunkRecord(
            chunk_id="demo-ccpa-1",
            jurisdiction=Jurisdiction.CCPA,
            source_label="CCPA / CPRA - sensitive personal information (demo excerpt)",
            heading="SPI and limitations",
            text=(
                "Businesses shall not collect or use sensitive personal information beyond what is reasonably "
                "necessary to provide the goods or services requested, except as permitted, and shall provide "
                "notice and respect consumer rights including limitation and opt-out where applicable."
            ),
        ),
    ]
