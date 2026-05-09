from backend.app.retrieval.local_index import LocalSearchResult
from backend.app.retrieval.rerank import rerank_results


def _result(
    segment_id: str,
    *,
    score: float,
    lexical_score: float | None = None,
    dense_score: float | None = None,
    motion_score: float = 0.0,
    highlight_score: float = 0.0,
    matched_tags: tuple[str, ...] = (),
) -> LocalSearchResult:
    return LocalSearchResult(
        segment_id=segment_id,
        video_id="video-1",
        start_time=0.0,
        end_time=5.0,
        score=score,
        reason="test fixture",
        evidence=[],
        creative_suggestion=None,
        motion_score=motion_score,
        highlight_score=highlight_score,
        lexical_score=lexical_score,
        dense_score=dense_score,
        matched_tags=matched_tags,
    )


def test_rerank_combines_score_components_and_intent_tags():
    generic = _result(
        "generic",
        score=0.72,
        lexical_score=0.72,
        dense_score=0.15,
        motion_score=0.1,
        highlight_score=0.1,
        matched_tags=("tutorial",),
    )
    intent_match = _result(
        "intent-match",
        score=0.54,
        lexical_score=0.42,
        dense_score=0.66,
        motion_score=0.9,
        highlight_score=0.85,
        matched_tags=("battle", "highlight"),
    )

    reranked = rerank_results([generic, intent_match], query_text="battle highlight")

    assert [result.segment_id for result in reranked] == ["intent-match", "generic"]
    assert reranked[0].score > reranked[1].score


def test_rerank_is_deterministic_for_equal_scores():
    results = [
        _result("segment-b", score=0.5, lexical_score=0.5),
        _result("segment-a", score=0.5, lexical_score=0.5),
    ]

    reranked = rerank_results(results, query_text="anything")

    assert [result.segment_id for result in reranked] == ["segment-a", "segment-b"]
