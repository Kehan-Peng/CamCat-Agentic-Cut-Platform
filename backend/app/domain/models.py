from typing import Any

from pydantic import BaseModel, Field, model_validator


class Video(BaseModel):
    video_id: str
    user_id: str
    source_type: str = "upload"
    filename: str
    storage_uri: str
    status: str = "uploaded"
    duration_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SegmentEvidence(BaseModel):
    evidence_type: str
    text: str
    start_time: float | None = None
    end_time: float | None = None
    frame_uri: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaSegment(BaseModel):
    segment_id: str
    video_id: str
    user_id: str
    start_time: float
    end_time: float
    asr_transcript: str = ""
    ocr_text: str = ""
    frame_captions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    motion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    highlight_score: float = Field(default=0.0, ge=0.0, le=1.0)
    representative_frame_uri: str | None = None
    evidence: list[SegmentEvidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time_range(self) -> "MediaSegment":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class SearchQuery(BaseModel):
    query_text: str
    user_id: str
    session_id: str | None = None
    scenario: str = "content_search"
    top_k: int = 5
    retrieval_mode: str = "hybrid"
    filters: dict[str, Any] = Field(default_factory=dict)


class CreativeSuggestion(BaseModel):
    recommended_bgm_style: str | None = None
    transition_suggestions: list[str] = Field(default_factory=list)
    editing_notes: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    segment_id: str
    video_id: str
    start_time: float
    end_time: float
    score: float
    reason: str
    evidence: list[SegmentEvidence] = Field(default_factory=list)
    creative_suggestion: CreativeSuggestion | None = None
