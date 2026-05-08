from pathlib import Path

from backend.app.domain.models import Video
from backend.app.media.interfaces import MediaPreprocessor
from backend.app.media.preprocessing import (
    DeterministicMediaPreprocessor,
    FfmpegCommandBuilder,
    PreprocessingResult,
)


def make_video(video_id: str = "video-preprocess") -> Video:
    return Video(
        video_id=video_id,
        user_id="user-1",
        filename="clip.mp4",
        storage_uri="memory://user-1/clip.mp4",
        duration_seconds=12.0,
    )


def test_deterministic_preprocessor_returns_stable_result_for_same_video():
    preprocessor = DeterministicMediaPreprocessor()
    video = make_video()

    first = preprocessor.preprocess_result(video)
    second = preprocessor.preprocess_result(video)

    assert first == second
    assert first.video == video
    assert first.video_id == "video-preprocess"


def test_preprocessing_result_references_video_and_mock_media_uris():
    result = DeterministicMediaPreprocessor().preprocess_result(make_video("video-42"))

    assert isinstance(result, PreprocessingResult)
    assert result.video_id == "video-42"
    assert result.audio_uri == "mock://audio/video-42.wav"
    assert result.frame_uris == [
        "mock://frames/video-42/000001.jpg",
        "mock://frames/video-42/000002.jpg",
        "mock://frames/video-42/000003.jpg",
    ]


def test_deterministic_preprocessor_satisfies_video_preprocessor_protocol():
    video = make_video()
    preprocessor = DeterministicMediaPreprocessor()

    assert isinstance(preprocessor, MediaPreprocessor)
    assert preprocessor.preprocess(video) == video


def test_ffmpeg_command_builder_returns_args_without_executing():
    args = FfmpegCommandBuilder().build_audio_extraction_args(
        input_uri="memory://user-1/clip.mp4",
        output_uri="mock://audio/video-42.wav",
    )

    assert args == [
        "ffmpeg",
        "-y",
        "-i",
        "memory://user-1/clip.mp4",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "mock://audio/video-42.wav",
    ]


def test_preprocessor_does_not_use_subprocess_or_write_files(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("preprocessing must not execute or write")

    monkeypatch.setattr("subprocess.run", fail)
    monkeypatch.setattr(Path, "write_text", fail)
    monkeypatch.setattr(Path, "write_bytes", fail)

    result = DeterministicMediaPreprocessor().preprocess_result(make_video())

    assert result.audio_uri.startswith("mock://audio/")
