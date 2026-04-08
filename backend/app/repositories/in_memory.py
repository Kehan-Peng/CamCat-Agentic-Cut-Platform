from backend.app.domain.models import MediaSegment, Video


class InMemoryMediaRepository:
    def __init__(self) -> None:
        self._videos: dict[tuple[str, str], Video] = {}
        self._segments: dict[tuple[str, str], MediaSegment] = {}

    def save_video(self, video: Video) -> Video:
        self._videos[(video.user_id, video.video_id)] = video
        return video

    def get_video(self, user_id: str, video_id: str) -> Video | None:
        return self._videos.get((user_id, video_id))

    def list_videos(self, user_id: str) -> list[Video]:
        return [
            video
            for (stored_user_id, _), video in self._videos.items()
            if stored_user_id == user_id
        ]

    def save_segment(self, segment: MediaSegment) -> MediaSegment:
        self._segments[(segment.user_id, segment.segment_id)] = segment
        return segment

    def get_segment(self, user_id: str, segment_id: str) -> MediaSegment | None:
        return self._segments.get((user_id, segment_id))

    def list_segments(self, user_id: str, video_id: str) -> list[MediaSegment]:
        return [
            segment
            for (stored_user_id, _), segment in self._segments.items()
            if stored_user_id == user_id and segment.video_id == video_id
        ]
