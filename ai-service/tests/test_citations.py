from app.services.agent_service import add_source
from app.services.citation_service import (
    build_citations,
    confidence_level,
    make_snippet,
    overall_confidence,
    relevance_from_distance,
)


def test_relevance_is_cosine_similarity_of_unit_vectors():
    assert relevance_from_distance(0.0) == 1.0  # identical
    assert relevance_from_distance(2.0) == 0.0  # orthogonal
    assert relevance_from_distance(0.8) == 0.6
    assert relevance_from_distance(None) is None


def test_relevance_is_clamped():
    assert relevance_from_distance(-0.5) == 1.0
    assert relevance_from_distance(9.0) == 0.0


def test_confidence_levels():
    assert confidence_level(0.9) == "high"
    assert confidence_level(0.6) == "high"
    assert confidence_level(0.5) == "medium"
    assert confidence_level(0.4) == "medium"
    assert confidence_level(0.39) == "low"
    assert confidence_level(None) is None


def test_snippet_collapses_whitespace_and_truncates():
    assert make_snippet("  a\n\n b\t c ") == "a b c"
    assert make_snippet(None) is None
    assert make_snippet("") is None

    long = make_snippet("word " * 200)
    assert long.endswith("...")
    assert len(long) <= 243


def src(page, score, doc="d1", text="text"):
    return {"document_id": doc, "page_number": page, "score": score, "text": text}


def test_add_source_keeps_closest_match_per_page():
    sources: list[dict] = []
    add_source(sources, src(1, 1.2, text="weak"))
    add_source(sources, src(1, 0.5, text="strong"))
    add_source(sources, src(1, 0.9, text="medium"))

    assert len(sources) == 1
    assert sources[0]["score"] == 0.5
    assert sources[0]["snippet"] == "strong"


def test_add_source_keeps_distinct_pages_and_documents():
    sources: list[dict] = []
    add_source(sources, src(1, 0.5))
    add_source(sources, src(2, 0.5))
    add_source(sources, src(1, 0.5, doc="d2"))
    assert len(sources) == 3


def test_unscored_hit_never_overrides_a_scored_one():
    sources: list[dict] = []
    add_source(sources, src(1, 0.7))
    add_source(sources, src(1, None))
    assert sources[0]["score"] == 0.7


def test_build_citations_sorted_best_first_unscored_last():
    raw = [
        {"document_id": "a", "page": 1, "score": 1.4, "snippet": "x"},
        {"document_id": "b", "page": 1, "score": None, "snippet": "y"},
        {"document_id": "c", "page": 1, "score": 0.4, "snippet": "z"},
    ]
    citations = build_citations(raw)

    assert [c.document_id for c in citations] == ["c", "a", "b"]
    assert citations[0].confidence == 0.8
    assert citations[0].confidence_level == "high"
    assert citations[1].confidence_level == "low"
    assert citations[2].confidence is None


def test_overall_confidence_is_best_source_or_none():
    citations = build_citations(
        [
            {"document_id": "a", "page": 1, "score": 1.4},
            {"document_id": "c", "page": 2, "score": 0.9},
        ]
    )
    assert overall_confidence(citations) == (0.55, "medium")
    assert overall_confidence([]) == (None, None)
    assert overall_confidence(build_citations([{"document_id": "a", "page": 1, "score": None}])) == (None, None)
