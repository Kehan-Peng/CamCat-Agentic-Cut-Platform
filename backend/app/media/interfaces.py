from typing import Protocol, runtime_checkable

from backend.app.domain.models import Video
from backend.app.media.contracts import (
    AudioExtractionResult,
    EmbeddingVector,
    FrameExtractionResult,
)


@runtime_checkable
class MediaPreprocessor(Protocol):
    def preprocess(self, video: Video) -> Video:
        ...


@runtime_checkable
class ASRExtractor(Protocol):
    def extract(self, video: Video) -> AudioExtractionResult:
        ...


@runtime_checkable
class OCRExtractor(Protocol):
    def extract(self, video: Video) -> FrameExtractionResult:
        ...


@runtime_checkable
class FrameCaptionExtractor(Protocol):
    def extract(self, video: Video) -> FrameExtractionResult:
        ...


@runtime_checkable
class VisualEmbeddingExtractor(Protocol):
    def extract(self, video: Video) -> list[EmbeddingVector]:
        ...
