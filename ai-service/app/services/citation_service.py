"""Turns raw retrieval hits into citations with a relevance ("confidence") score.

FAISS returns a squared L2 distance. For unit-length embeddings (OpenAI
embeddings, all-MiniLM-L6-v2) that equals ``2 - 2 * cosine_similarity``, so
``1 - distance / 2`` is the cosine similarity between the question and the
passage. We report that as ``confidence``.

IMPORTANT: this measures how closely the passage matches the question, not
whether the generated answer is correct. A high score means "a very relevant
passage was found", nothing more.
"""

from app.models.agent import SourceRef

HIGH_THRESHOLD = 0.6
MEDIUM_THRESHOLD = 0.4
SNIPPET_LENGTH = 240


def relevance_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None
    return round(min(1.0, max(0.0, 1.0 - float(distance) / 2.0)), 3)


def confidence_level(confidence: float | None) -> str | None:
    if confidence is None:
        return None
    if confidence >= HIGH_THRESHOLD:
        return "high"
    if confidence >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def make_snippet(text: str | None) -> str | None:
    if not text:
        return None
    collapsed = " ".join(text.split())
    if len(collapsed) <= SNIPPET_LENGTH:
        return collapsed
    return collapsed[:SNIPPET_LENGTH].rstrip() + "..."


def build_citations(sources: list[dict]) -> list[SourceRef]:
    """Best match first; passages without a score (exact lookups) go last."""
    citations = []

    for source in sources:
        confidence = relevance_from_distance(source.get("score"))
        citations.append(
            SourceRef(
                document_id=source["document_id"],
                document_name=source.get("document_name"),
                page=source.get("page"),
                score=source.get("score"),
                snippet=source.get("snippet"),
                confidence=confidence,
                confidence_level=confidence_level(confidence),
            )
        )

    citations.sort(
        key=lambda c: (c.confidence is None, -(c.confidence or 0.0))
    )
    return citations


def overall_confidence(citations: list[SourceRef]) -> tuple[float | None, str | None]:
    scores = [c.confidence for c in citations if c.confidence is not None]
    if not scores:
        return None, None
    best = max(scores)
    return best, confidence_level(best)
