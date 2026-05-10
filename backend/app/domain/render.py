"""
Render 数据模型

定义渲染任务、剪辑片段和编辑后的视频产物。
"""
from typing import Any
from pydantic import BaseModel, Field


class ClipSegment(BaseModel):
    """剪辑片段"""
    clip_id: str
    source_video_id: str
    start_time: float
    end_time: float
    output_start_time: float
    output_end_time: float
    filters: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderJob(BaseModel):
    """渲染任务"""
    job_id: str
    editing_session_id: str
    user_id: str
    status: str  # pending, running, completed, failed, cancelled
    clip_segments: list[str]
    output_path: str | None = None
    error_message: str | None = None
    progress: float = 0.0
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EditedVideoArtifact(BaseModel):
    """编辑后的视频产物"""
    artifact_id: str
    editing_session_id: str
    render_job_id: str
    user_id: str
    output_path: str
    status: str  # completed, failed, processing
    duration_seconds: float | None = None
    file_size_bytes: int | None = None
    resolution: str | None = None
    codec: str | None = None
    checksum: str | None = None
    preview_path: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
