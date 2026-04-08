from backend.app.domain.models import Video
from backend.app.media.mock_pipeline import generate_mock_media_segments


def make_video(video_id: str = "video-1", duration_seconds: float | None = 20.0) -> Video:
    return Video(
        video_id=video_id,
        user_id="user-1",
        filename=f"{video_id}.mp4",
        storage_uri=f"memory://user-1/{video_id}.mp4",
        duration_seconds=duration_seconds,
    )


def test_mock_pipeline_generates_valid_segments():
    video = make_video()

    segments = generate_mock_media_segments(video)

    assert segments
    for segment in segments:
        assert segment.video_id == video.video_id
        assert segment.user_id == video.user_id
        assert segment.end_time > segment.start_time
        assert segment.start_time >= 0.0


def test_mock_pipeline_is_deterministic_for_same_video():
    video = make_video(video_id="deterministic-video")

    first = generate_mock_media_segments(video)
    second = generate_mock_media_segments(video)

    assert [segment.model_dump() for segment in first] == [
        segment.model_dump() for segment in second
    ]


def test_mock_pipeline_generates_3_to_5_segments():
    segments = generate_mock_media_segments(make_video(video_id="count-video"))

    assert 3 <= len(segments) <= 5


def test_mock_pipeline_populates_multimodal_metadata():
    segments = generate_mock_media_segments(make_video())

    for segment in segments:
        assert segment.asr_transcript
        assert segment.ocr_text
        assert segment.frame_captions
        assert segment.tags
        assert segment.evidence


def test_mock_pipeline_includes_high_energy_candidate_segment():
    segments = generate_mock_media_segments(make_video())

    candidate = next(
        segment for segment in segments if "high_energy" in segment.tags
    )

    assert candidate.asr_transcript == "最后一波团战开启，反打成功，全场沸腾"
    assert candidate.ocr_text == "ACE / 胜利 / 高能时刻"
    assert candidate.frame_captions == ["快节奏战斗", "冲刺"]
    assert {"gameplay", "hot_blooded", "highlight"}.issubset(candidate.tags)
    assert candidate.motion_score >= 0.85
    assert candidate.highlight_score >= 0.85


def test_mock_pipeline_scores_are_within_zero_to_one():
    segments = generate_mock_media_segments(make_video())

    for segment in segments:
        assert 0.0 <= segment.motion_score <= 1.0
        assert 0.0 <= segment.highlight_score <= 1.0
