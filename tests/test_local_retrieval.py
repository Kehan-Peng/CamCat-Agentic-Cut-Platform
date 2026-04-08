from backend.app.domain.models import MediaSegment, SegmentEvidence, SearchQuery
from backend.app.retrieval.explain import build_reason
from backend.app.retrieval.local_index import LocalMediaIndex
from backend.app.retrieval.query_rewrite import rewrite_query
from backend.app.retrieval.rerank import rerank_results


def _segment(
    segment_id: str,
    *,
    asr_transcript: str = "",
    ocr_text: str = "",
    frame_captions: list[str] | None = None,
    tags: list[str] | None = None,
    motion_score: float = 0.2,
    highlight_score: float = 0.2,
    evidence: list[SegmentEvidence] | None = None,
) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id="video-1",
        user_id="user-1",
        start_time=0.0,
        end_time=5.0,
        asr_transcript=asr_transcript,
        ocr_text=ocr_text,
        frame_captions=frame_captions or [],
        tags=tags or [],
        motion_score=motion_score,
        highlight_score=highlight_score,
        evidence=evidence or [],
    )


def test_query_rewrite_expands_hot_blooded_cut_query():
    rewritten = rewrite_query("帮我找适合做热血卡点的视频素材")

    assert rewritten.original_query == "帮我找适合做热血卡点的视频素材"
    assert "热血" in rewritten.expanded_queries
    assert "卡点" in rewritten.expanded_queries
    assert "high_energy" in rewritten.expanded_queries
    assert "highlight" in rewritten.expanded_queries


def test_local_retrieval_searches_asr_ocr_captions_and_tags():
    segments = [
        _segment("asr-match", asr_transcript="团战开始"),
        _segment("ocr-match", ocr_text="胜利"),
        _segment("caption-match", frame_captions=["快节奏战斗"]),
        _segment("tag-match", tags=["hot_blooded"]),
        _segment("miss", asr_transcript="安静开场"),
    ]

    results = LocalMediaIndex(segments).search(
        SearchQuery(query_text="团战 胜利 快节奏 hot_blooded", user_id="user-1", top_k=10)
    )

    assert {result.segment_id for result in results} == {
        "asr-match",
        "ocr-match",
        "caption-match",
        "tag-match",
    }


def test_rerank_prefers_high_motion_and_highlight_candidate():
    low_energy = _segment("low", asr_transcript="热血 团战", motion_score=0.1, highlight_score=0.1)
    high_energy = _segment(
        "high",
        asr_transcript="热血 团战",
        motion_score=0.95,
        highlight_score=0.9,
    )

    results = LocalMediaIndex([low_energy, high_energy]).search(
        SearchQuery(query_text="热血 团战", user_id="user-1", top_k=2)
    )
    reranked = rerank_results(results)

    assert reranked[0].segment_id == "high"
    assert reranked[0].score > reranked[1].score


def test_reason_only_references_existing_evidence():
    segment = _segment(
        "caption-only",
        frame_captions=["快节奏战斗"],
        motion_score=0.93,
        highlight_score=0.91,
        evidence=[
            SegmentEvidence(
                evidence_type="frame_caption",
                text="快节奏战斗",
                confidence=0.8,
            )
        ],
    )

    reason, evidence = build_reason(segment, matched_fields={"frame_captions"})

    assert "视觉" in reason
    assert "高运动" in reason
    assert "高光" in reason
    assert "ASR" not in reason
    assert "OCR" not in reason
    assert [item.evidence_type for item in evidence] == ["frame_caption"]
