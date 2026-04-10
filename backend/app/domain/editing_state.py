"""
Editing State 数据模型

定义全局编辑状态、状态补丁、补丁操作和工作流产物状态。
"""
from typing import Any
from pydantic import BaseModel, Field


class WorkflowArtifactStatus(BaseModel):
    """工作流产物状态"""
    subtitle_draft: str = "not_started"  # not_started, in_progress, ready, stale, failed
    editing_plan: str = "not_started"
    clip_segments: str = "not_started"
    title_candidates: str = "not_started"
    edited_video: str = "not_started"
    preview_video: str = "not_started"


class PatchOperation(BaseModel):
    """补丁操作"""
    op: str  # add_segment, remove_segment, replace_segment, reorder_segments, trim_segment, update_subtitle_style, etc.
    target: str  # selected_segments, clip_segments, subtitle_draft, editing_plan, etc.
    value: Any = None
    clip_segment_id: str | None = None
    segment_id: str | None = None
    position: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EditingStatePatch(BaseModel):
    """编辑状态补丁"""
    patch_id: str
    editing_session_id: str
    base_state_version: int
    operations: list[PatchOperation]
    affected_artifacts: list[str]
    needs_refresh: dict[str, bool]
    requires_retrieval: bool = False
    requires_render: bool = False
    patch_type: str = "incremental"  # incremental, full_regeneration
    reason: str | None = None
    requires_user_confirmation: bool = False
    created_at: str | None = None


class GlobalEditingState(BaseModel):
    """全局编辑状态"""
    editing_session_id: str
    user_id: str
    video_id: str
    selected_segments: list[str]
    state_version: int
    subtitle_draft: str | None = None
    editing_plan: str | None = None
    clip_segments: list[str] = Field(default_factory=list)
    title_candidates: list[str] = Field(default_factory=list)
    tag_candidates: list[str] = Field(default_factory=list)
    artifact_status: WorkflowArtifactStatus = Field(default_factory=WorkflowArtifactStatus)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
