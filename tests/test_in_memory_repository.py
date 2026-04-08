from backend.app.domain.models import MediaSegment, Video
from backend.app.repositories.in_memory import InMemoryMediaRepository


def make_video(video_id: str = "video-1", user_id: str = "user-1") -> Video:
    return Video(
        video_id=video_id,
        user_id=user_id,
        filename=f"{video_id}.mp4",
        storage_uri=f"memory://{user_id}/{video_id}.mp4",
        duration_seconds=12.0,
    )


def make_segment(
    segment_id: str = "segment-1",
    video_id: str = "video-1",
    user_id: str = "user-1",
    start_time: float = 0.0,
    end_time: float = 3.0,
) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id=video_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        asr_transcript="mock transcript",
        tags=["mock"],
    )


def test_repository_saves_and_gets_video_for_same_user():
    repository = InMemoryMediaRepository()
    video = make_video()

    repository.save_video(video)

    assert repository.get_video(user_id="user-1", video_id="video-1") == video
    assert repository.list_videos(user_id="user-1") == [video]


def test_repository_blocks_cross_user_video_access():
    repository = InMemoryMediaRepository()
    repository.save_video(make_video(user_id="user-1"))

    assert repository.get_video(user_id="user-2", video_id="video-1") is None
    assert repository.list_videos(user_id="user-2") == []


def test_repository_saves_and_lists_segments_for_video():
    repository = InMemoryMediaRepository()
    first = make_segment(segment_id="segment-1")
    second = make_segment(segment_id="segment-2", start_time=3.0, end_time=6.0)

    repository.save_segment(first)
    repository.save_segment(second)

    assert repository.get_segment(user_id="user-1", segment_id="segment-1") == first
    assert repository.list_segments(user_id="user-1", video_id="video-1") == [
        first,
        second,
    ]


def test_repository_blocks_cross_user_segment_access():
    repository = InMemoryMediaRepository()
    repository.save_segment(make_segment(user_id="user-1"))

    assert repository.get_segment(user_id="user-2", segment_id="segment-1") is None
    assert repository.list_segments(user_id="user-2", video_id="video-1") == []


def test_repository_returns_empty_list_for_unknown_video():
    repository = InMemoryMediaRepository()
    repository.save_segment(make_segment(video_id="video-1"))

    assert repository.list_segments(user_id="user-1", video_id="unknown-video") == []
