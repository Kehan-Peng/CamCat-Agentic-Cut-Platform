from backend.app.domain.models import MediaSegment, Video
from backend.app.media.contracts import (
    ASRChunk,
    AudioExtractionResult,
    EmbeddingVector,
    FrameCaption,
    FrameExtractionResult,
    OCRBlock,
)
from backend.app.media.interfaces import (
    ASRExtractor,
    FrameCaptionExtractor,
    MediaPreprocessor,
    OCRExtractor,
    VisualEmbeddingExtractor,
)
from backend.app.media.mock_pipeline import generate_mock_media_segments


def make_video() -> Video:
    return Video(
        video_id="video-interfaces",
        user_id="user-1",
        filename="clip.mp4",
        storage_uri="memory://user-1/clip.mp4",
        duration_seconds=12.0,
    )


def test_audio_contract_serializes_with_model_dump():
    result = AudioExtractionResult(
        video_id="video-1",
        chunks=[
            ASRChunk(
                text="hello",
                start_time=0.0,
                end_time=1.2,
                confidence=0.91,
            )
        ],
    )

    assert result.model_dump() == {
        "video_id": "video-1",
        "chunks": [
            {
                "text": "hello",
                "start_time": 0.0,
                "end_time": 1.2,
                "confidence": 0.91,
            }
        ],
    }


def test_frame_contract_serializes_with_model_dump():
    result = FrameExtractionResult(
        video_id="video-1",
        ocr_blocks=[
            OCRBlock(
                text="SCORE",
                start_time=2.0,
                end_time=2.0,
                frame_uri="mock://frames/video-1/1.jpg",
                confidence=0.82,
            )
        ],
        captions=[
            FrameCaption(
                text="player opens inventory",
                start_time=2.0,
                end_time=3.0,
                frame_uri="mock://frames/video-1/1.jpg",
                confidence=0.77,
            )
        ],
        embeddings=[
            EmbeddingVector(
                values=[0.1, 0.2, 0.3],
                start_time=2.0,
                end_time=3.0,
                frame_uri="mock://frames/video-1/1.jpg",
            )
        ],
    )

    dumped = result.model_dump()

    assert dumped["video_id"] == "video-1"
    assert dumped["ocr_blocks"][0]["text"] == "SCORE"
    assert dumped["captions"][0]["text"] == "player opens inventory"
    assert dumped["embeddings"][0]["values"] == [0.1, 0.2, 0.3]


def test_extractor_protocols_are_importable_and_structurally_satisfied():
    video = make_video()

    class FakePreprocessor:
        def preprocess(self, video: Video) -> Video:
            return video

    class FakeASRExtractor:
        def extract(self, video: Video) -> AudioExtractionResult:
            return AudioExtractionResult(video_id=video.video_id, chunks=[])

    class FakeOCRExtractor:
        def extract(self, video: Video) -> FrameExtractionResult:
            return FrameExtractionResult(video_id=video.video_id)

    class FakeCaptionExtractor:
        def extract(self, video: Video) -> FrameExtractionResult:
            return FrameExtractionResult(video_id=video.video_id)

    class FakeEmbeddingExtractor:
        def extract(self, video: Video) -> list[EmbeddingVector]:
            return [EmbeddingVector(values=[1.0], start_time=0.0, end_time=1.0)]

    preprocessor = FakePreprocessor()
    asr = FakeASRExtractor()
    ocr = FakeOCRExtractor()
    captions = FakeCaptionExtractor()
    embeddings = FakeEmbeddingExtractor()

    assert isinstance(preprocessor, MediaPreprocessor)
    assert preprocessor.preprocess(video) == video
    assert isinstance(asr, ASRExtractor)
    assert asr.extract(video).video_id == video.video_id
    assert isinstance(ocr, OCRExtractor)
    assert ocr.extract(video).ocr_blocks == []
    assert isinstance(captions, FrameCaptionExtractor)
    assert captions.extract(video).captions == []
    assert isinstance(embeddings, VisualEmbeddingExtractor)
    assert embeddings.extract(video)[0].values == [1.0]


def test_mock_pipeline_still_returns_valid_media_segments():
    segments = generate_mock_media_segments(make_video())

    assert segments
    assert all(isinstance(segment, MediaSegment) for segment in segments)
    assert all(segment.end_time > segment.start_time for segment in segments)
