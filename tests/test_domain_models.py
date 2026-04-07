import pytest
from pydantic import ValidationError

from backend.app.domain.models import (
    CreativeSuggestion,
    MediaSegment,
    RetrievalResult,
    SearchQuery,
    SegmentEvidence,
    Video,
)


def test_valid_video_can_be_created_and_serialized():
    video = Video(
        video_id="video-1",
        user_id="user-1",
        filename="clip.mp4",
        storage_uri="s3://bucket/clip.mp4",
        duration_seconds=12.5,
    )

    assert video.model_dump() == {
        "video_id": "video-1",
        "user_id": "user-1",
        "source_type": "upload",
        "filename": "clip.mp4",
        "storage_uri": "s3://bucket/clip.mp4",
        "status": "uploaded",
        "duration_seconds": 12.5,
        "metadata": {},
    }


def test_valid_media_segment_can_be_created_and_serialized():
    segment = MediaSegment(
        segment_id="segment-1",
        video_id="video-1",
        user_id="user-1",
        start_time=1.0,
        end_time=4.0,
        frame_captions=["wide shot"],
        tags=["intro"],
        motion_score=0.25,
        highlight_score=0.75,
        evidence=[
            SegmentEvidence(
                evidence_type="asr",
                text="hello world",
                start_time=1.0,
                end_time=2.0,
                confidence=0.9,
            )
        ],
    )

    assert segment.model_dump() == {
        "segment_id": "segment-1",
        "video_id": "video-1",
        "user_id": "user-1",
        "start_time": 1.0,
        "end_time": 4.0,
        "asr_transcript": "",
        "ocr_text": "",
        "frame_captions": ["wide shot"],
        "tags": ["intro"],
        "motion_score": 0.25,
        "highlight_score": 0.75,
        "representative_frame_uri": None,
        "evidence": [
            {
                "evidence_type": "asr",
                "text": "hello world",
                "start_time": 1.0,
                "end_time": 2.0,
                "frame_uri": None,
                "confidence": 0.9,
                "metadata": {},
            }
        ],
        "metadata": {},
    }


@pytest.mark.parametrize("end_time", [0.0, 1.0])
def test_media_segment_rejects_end_time_not_greater_than_start_time(end_time):
    with pytest.raises(ValidationError):
        MediaSegment(
            segment_id="segment-1",
            video_id="video-1",
            user_id="user-1",
            start_time=1.0,
            end_time=end_time,
        )


@pytest.mark.parametrize("motion_score", [-0.1, 1.1])
def test_media_segment_rejects_motion_score_outside_zero_to_one(motion_score):
    with pytest.raises(ValidationError):
        MediaSegment(
            segment_id="segment-1",
            video_id="video-1",
            user_id="user-1",
            start_time=1.0,
            end_time=2.0,
            motion_score=motion_score,
        )


@pytest.mark.parametrize("highlight_score", [-0.1, 1.1])
def test_media_segment_rejects_highlight_score_outside_zero_to_one(highlight_score):
    with pytest.raises(ValidationError):
        MediaSegment(
            segment_id="segment-1",
            video_id="video-1",
            user_id="user-1",
            start_time=1.0,
            end_time=2.0,
            highlight_score=highlight_score,
        )


def test_search_query_uses_phase_one_defaults():
    query = SearchQuery(query_text="find a skyline shot", user_id="user-1")

    assert query.top_k == 5
    assert query.retrieval_mode == "hybrid"
    assert query.scenario == "content_search"
    assert query.model_dump()["filters"] == {}


def test_retrieval_result_serializes_score_reason_and_creative_suggestion():
    result = RetrievalResult(
        segment_id="segment-1",
        video_id="video-1",
        start_time=1.0,
        end_time=3.0,
        score=0.88,
        reason="Strong transcript match",
        creative_suggestion=CreativeSuggestion(
            recommended_bgm_style="upbeat",
            transition_suggestions=["cut on beat"],
            editing_notes=["use as opener"],
        ),
    )

    assert result.model_dump() == {
        "segment_id": "segment-1",
        "video_id": "video-1",
        "start_time": 1.0,
        "end_time": 3.0,
        "score": 0.88,
        "reason": "Strong transcript match",
        "evidence": [],
        "creative_suggestion": {
            "recommended_bgm_style": "upbeat",
            "transition_suggestions": ["cut on beat"],
            "editing_notes": ["use as opener"],
        },
    }
