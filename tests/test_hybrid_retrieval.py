from backend.app.domain.models import MediaSegment, SearchQuery
from backend.app.retrieval.embeddings import HashEmbeddingProvider
from backend.app.retrieval.filters import segment_matches_filters
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.local_index import LocalMediaIndex


def _segment(
    segment_id: str,
    *,
    video_id: str = "video-1",
    asr_transcript: str = "",
    ocr_text: str = "",
    frame_captions: list[str] | None = None,
    tags: list[str] | None = None,
    motion_score: float = 0.2,
    highlight_score: float = 0.2,
) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id=video_id,
        user_id="user-1",
        start_time=0.0,
        end_time=5.0,
        asr_transcript=asr_transcript,
        ocr_text=ocr_text,
        frame_captions=frame_captions or [],
        tags=tags or [],
        motion_score=motion_score,
        highlight_score=highlight_score,
    )


def test_hash_embedding_is_deterministic_for_same_text():
    provider = HashEmbeddingProvider(dimensions=16)

    first = provider.embed_text("fast battle victory")
    second = provider.embed_text("fast battle victory")

    assert first == second
    assert len(first) == 16


def test_dense_similarity_ranks_token_overlap_above_unrelated_segment():
    segments = [
        _segment("match", asr_transcript="fast battle victory"),
        _segment("miss", asr_transcript="quiet cooking tutorial"),
    ]

    results = HybridRetriever(segments, embedding_provider=HashEmbeddingProvider()).dense_search(
        SearchQuery(query_text="battle victory", user_id="user-1", top_k=2)
    )

    assert [result.segment_id for result in results] == ["match", "miss"]
    assert results[0].score > results[1].score


def test_metadata_filter_supports_video_tags_and_min_scores():
    keeper = _segment(
        "keeper",
        video_id="video-1",
        tags=["hot_blooded", "battle"],
        motion_score=0.7,
        highlight_score=0.9,
    )
    wrong_video = _segment(
        "wrong-video",
        video_id="video-2",
        tags=["hot_blooded"],
        motion_score=0.9,
        highlight_score=0.9,
    )
    wrong_tag = _segment(
        "wrong-tag",
        video_id="video-1",
        tags=["calm"],
        motion_score=0.9,
        highlight_score=0.9,
    )
    low_score = _segment(
        "low-score",
        video_id="video-1",
        tags=["hot_blooded"],
        motion_score=0.2,
        highlight_score=0.4,
    )
    filters = {
        "video_id": "video-1",
        "tags": ["hot_blooded"],
        "min_motion_score": 0.5,
        "min_highlight_score": 0.8,
    }

    assert segment_matches_filters(keeper, filters)
    assert not segment_matches_filters(wrong_video, filters)
    assert not segment_matches_filters(wrong_tag, filters)
    assert not segment_matches_filters(low_score, filters)


def test_local_index_applies_bm25_like_term_frequency_and_filters():
    frequent = _segment(
        "frequent",
        asr_transcript="battle battle battle victory",
        tags=["hot_blooded"],
    )
    once = _segment("once", asr_transcript="battle victory", tags=["hot_blooded"])
    filtered = _segment("filtered", asr_transcript="battle battle victory", tags=["calm"])

    results = LocalMediaIndex([once, frequent, filtered]).search(
        SearchQuery(
            query_text="battle victory",
            user_id="user-1",
            top_k=3,
            filters={"tags": ["hot_blooded"]},
        )
    )

    assert [result.segment_id for result in results] == ["frequent", "once"]
    assert results[0].score > results[1].score


def test_hybrid_fusion_combines_lexical_and_dense_candidates():
    lexical = _segment("lexical", asr_transcript="goal celebration")
    dense = _segment("dense", frame_captions=["celebration sprint finish"])
    miss = _segment("miss", asr_transcript="quiet cooking tutorial")

    results = HybridRetriever([miss, dense, lexical]).search(
        SearchQuery(query_text="celebration finish", user_id="user-1", top_k=2)
    )

    assert {result.segment_id for result in results} == {"lexical", "dense"}
    assert all(result.video_id and result.reason and result.evidence is not None for result in results)
