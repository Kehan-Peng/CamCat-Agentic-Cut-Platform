from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class JobResponse(BaseModel):
    job_id: UUID
    kind: str
    status: str
    progress: float
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 0
    max_attempts: int = 3
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class VideoResponse(BaseModel):
    video_id: UUID
    status: str
    filename: str
    segment_count: int = 0
    duration_seconds: float | None = None
    job_id: UUID | None = None
    playback_url: str | None = None
    error: str | None = None


class SourceMediaReference(BaseModel):
    media_id: str
    filename: str
    content_type: str
    storage_key: str
    expires_at: datetime
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    has_audio: bool | None = None
    playback_url: str | None = None


class SourceUploadResponse(BaseModel):
    batch_id: str
    status: str
    job_id: UUID
    expires_at: datetime
    media: list[SourceMediaReference]


class SearchRequest(BaseModel):
    query_text: str | None = None
    query_image_base64: str | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    retrieval_mode: Literal["multimodal"] = "multimodal"
    thread_id: str = Field(min_length=1, max_length=255)
    filters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_query(self) -> SearchRequest:
        if not self.query_text and not self.query_image_base64:
            raise ValueError("query_text or query_image_base64 is required")
        return self


class RankedSegmentResponse(BaseModel):
    segment_id: UUID
    video_id: UUID
    start_time: float
    end_time: float
    score: float
    reranker_score: float
    caption: str
    tags: list[str]
    route_scores: dict[str, float]
    route_ranks: dict[str, int]
    thumbnail_url: str | None = None
    source_video_url: str | None = None
    event_type: str | None = None
    risk_score: float = 0.0
    semantic_metadata: dict[str, Any] = Field(default_factory=dict)
    license_name: str
    source_url: str


class AgenticSearchResponse(BaseModel):
    graph_run_id: UUID
    thread_id: str
    final_answer: str
    route_sequence: list[str]
    node_trace: list[dict[str, Any]]
    ranked_segments: list[RankedSegmentResponse]


class CreateEditingSessionRequest(BaseModel):
    project_id: UUID | None = None
    video_id: UUID | None = None
    source_job_id: UUID | None = None
    current_goal: str = Field(min_length=1, max_length=4000)


class EditingSessionResponse(BaseModel):
    editing_session_id: UUID
    state_version: int
    state: dict[str, Any]
    updated_at: datetime


class PatchOperationRequest(BaseModel):
    op: Literal["add", "replace", "remove"]
    path: str
    value: Any = None


class PatchEditingSessionRequest(BaseModel):
    base_version: int = Field(ge=1)
    operations: list[PatchOperationRequest] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)


class RollbackRequest(BaseModel):
    base_version: int = Field(ge=1)
    target_version: int = Field(ge=1)


class AgentEditRequest(BaseModel):
    base_version: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=8000)
    query_image_base64: str | None = None
    top_k: int = Field(default=12, ge=1, le=50)


class RenderRequest(BaseModel):
    base_version: int = Field(ge=1)
    resolution: Literal["1080x1920", "1920x1080", "1080x1080", "1080x1440", "1440x1080"] | None = (
        None
    )
    burn_subtitles: bool = True


class ImportOpenMediaRequest(BaseModel):
    download_url: HttpUrl
    source_url: HttpUrl
    license_name: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    project_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


class VersionResponse(BaseModel):
    version: int
    document: dict[str, Any]
    created_at: datetime


class PatchResponse(BaseModel):
    patch_id: UUID
    base_version: int
    result_version: int
    operations: list[dict[str, Any]]
    actor: str
    reason: str
    created_at: datetime


class GraphRunResponse(BaseModel):
    graph_run_id: UUID
    thread_id: str
    editing_session_id: UUID | None
    status: str
    state: dict[str, Any]
    node_trace: list[dict[str, Any]]
    error: str | None
    created_at: datetime
    finished_at: datetime | None
