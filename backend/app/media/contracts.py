from pydantic import BaseModel, Field


class ASRChunk(BaseModel):
    text: str
    start_time: float
    end_time: float
    confidence: float | None = None


class OCRBlock(BaseModel):
    text: str
    start_time: float | None = None
    end_time: float | None = None
    frame_uri: str | None = None
    confidence: float | None = None


class FrameCaption(BaseModel):
    text: str
    start_time: float | None = None
    end_time: float | None = None
    frame_uri: str | None = None
    confidence: float | None = None


class EmbeddingVector(BaseModel):
    values: list[float]
    start_time: float | None = None
    end_time: float | None = None
    frame_uri: str | None = None


class AudioExtractionResult(BaseModel):
    video_id: str
    chunks: list[ASRChunk] = Field(default_factory=list)


class FrameExtractionResult(BaseModel):
    video_id: str
    ocr_blocks: list[OCRBlock] = Field(default_factory=list)
    captions: list[FrameCaption] = Field(default_factory=list)
    embeddings: list[EmbeddingVector] = Field(default_factory=list)
