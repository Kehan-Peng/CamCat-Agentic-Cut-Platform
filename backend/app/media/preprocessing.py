from pydantic import BaseModel, Field

from backend.app.domain.models import Video


class PreprocessingResult(BaseModel):
    video_id: str
    video: Video
    audio_uri: str | None = None
    frame_uris: list[str] = Field(default_factory=list)


class DeterministicMediaPreprocessor:
    def __init__(self, frame_count: int = 3) -> None:
        self.frame_count = frame_count

    def preprocess(self, video: Video) -> Video:
        return video

    def preprocess_result(self, video: Video) -> PreprocessingResult:
        return PreprocessingResult(
            video_id=video.video_id,
            video=video,
            audio_uri=f"mock://audio/{video.video_id}.wav",
            frame_uris=[
                f"mock://frames/{video.video_id}/{index:06d}.jpg"
                for index in range(1, self.frame_count + 1)
            ],
        )


class FfmpegCommandBuilder:
    def __init__(self, binary: str = "ffmpeg") -> None:
        self.binary = binary

    def build_audio_extraction_args(self, input_uri: str, output_uri: str) -> list[str]:
        return [
            self.binary,
            "-y",
            "-i",
            input_uri,
            "-vn",
            "-acodec",
            "pcm_s16le",
            output_uri,
        ]
